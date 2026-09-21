"""参考文档上下文选择端口实现。

封装 skill.infrastructure.selector 的跨域调用。
本模块位于 infrastructure 层，可直接调用跨域服务。
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from ....common.utils.error_utils import summarize_exception
from ....skill.application.dtos.runtime import SkillPlanDecision
from ....skill.infrastructure.selector import (
    SelectorOption,
    build_selector_skill_interfaces,
    select_for_workspace_reference,
)
from ...application.ports import KnowledgeRetrieverPort, ReferenceContextPort
from ...domain.values.constants import (
    INCIDENT_REPORT_BODY_REFERENCE_DIR,
    INCIDENT_REPORT_COMMON_REFERENCE,
    INCIDENT_REPORT_REFERENCE_DIR,
    INCIDENT_REPORT_REFERENCE_SELECT_LIMIT,
    INCIDENT_REPORT_SECTION_REFERENCE_MAP,
    INCIDENT_REPORT_SKILL_MD_PATH,
    INCIDENT_SYSTEM_DOMAIN_MAP,
)
from ..utils.normalization import normalize_text

logger = logging.getLogger(__name__)


def _load_text_file(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        logger.debug("Failed to read text file: %s", path, exc_info=True)
        return ""


def _load_incident_skill_markdown() -> str:
    text = _load_text_file(INCIDENT_REPORT_SKILL_MD_PATH)
    if text:
        return text
    return "# incident-report\n事故报告 skill，用于根据当前生成目标选择参考文档并输出结构化正文。"


def _extract_reference_summary(text: str, *, max_lines: int = 3) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    filtered = [line for line in lines if not line.startswith("#")]
    selected = filtered[:max_lines] or lines[:max_lines]
    return " ".join(selected)[:260]


def _build_incident_reference_catalog() -> list[dict[str, str]]:
    if not INCIDENT_REPORT_BODY_REFERENCE_DIR.is_dir():
        return []
    catalog: list[dict[str, str]] = []
    for path in sorted(INCIDENT_REPORT_BODY_REFERENCE_DIR.glob("*.md")):
        text = _load_text_file(path)
        if not text:
            continue
        relative_path = path.relative_to(INCIDENT_REPORT_REFERENCE_DIR).as_posix()
        title = path.stem
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip() or title
                break
        catalog.append(
            {
                "path": relative_path,
                "title": title,
                "summary": _extract_reference_summary(text),
            }
        )
    return catalog


def _select_references_by_heuristic(
    *,
    section_id: str,
    available_paths: list[str],
) -> list[str]:
    section_key = section_id.strip().lower()
    tokens = [token for token in re.split(r"[_\-\s]+", section_key) if token]
    selected: list[str] = []

    for path in available_paths:
        if path.endswith("/common.md"):
            selected.append(path)
            break

    for path in available_paths:
        filename = path.rsplit("/", 1)[-1].lower()
        if any(token in filename for token in tokens):
            selected.append(path)

    if section_key == "quick":
        for path in available_paths:
            if "quick" in path:
                selected.append(path)
                break

    deduped: list[str] = []
    seen: set[str] = set()
    for path in selected:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)

    if not deduped and available_paths:
        deduped.append(available_paths[0])
    return deduped[:INCIDENT_REPORT_REFERENCE_SELECT_LIMIT]


def _build_reference_planner_query(
    *,
    section_id: str,
    timeline_index: int | None,
    prompt: str,
    context_json: str,
    skill_markdown: str,
) -> str:
    planner_payload = {
        "skill_id": "incident-report",
        "target_section": section_id,
        "timeline_index": timeline_index,
        "generation_prompt": prompt,
        "generation_context": context_json,
        "selection_goal": "选择最小必要参考文档集合用于当前正文生成",
    }
    return (
        f"incident-report SKILL.md:\n{skill_markdown}\n\n"
        f"本次参考选择请求:\n{json.dumps(planner_payload, ensure_ascii=False)}"
    )


def _build_reference_selector_options(
    reference_catalog: list[dict[str, str]],
) -> list[SelectorOption]:
    options: list[SelectorOption] = []
    for item in reference_catalog:
        path = normalize_text(item.get("path"))
        title = normalize_text(item.get("title"))
        summary = normalize_text(item.get("summary"))
        if not path:
            continue
        options.append(
            SelectorOption(
                id=path,
                display_name=title or path,
                short_description=summary or title or path,
                default_prompt=summary or title or path,
            )
        )
    return options


def _select_reference_files_from_plan(
    *,
    decision: SkillPlanDecision,
    available_paths: list[str],
    system_skill_id: str,
) -> list[str]:
    allowed_set = set(available_paths)
    selected: list[str] = []
    for skill_id in decision.active_skill_ids:
        if skill_id == system_skill_id:
            continue
        if skill_id not in allowed_set:
            continue
        if skill_id not in selected:
            selected.append(skill_id)
    return selected[:INCIDENT_REPORT_REFERENCE_SELECT_LIMIT]


def _required_reference_files(
    *,
    section_id: str,
    available_paths: list[str],
) -> list[str]:
    """当前 section 必须加载的规范文件。

    写作契约是跨报告通用的硬要求，不能交给规划器概率挑选。
    实测问题：quick 模式只加载 common.md + quick-mode.md，
    而 impact.md / root-cause.md / follow-up.md 进不了 prompt。
    """
    section_key = (section_id or "").strip().lower()
    configured = INCIDENT_REPORT_SECTION_REFERENCE_MAP.get(section_key)
    if not configured:
        configured = (INCIDENT_REPORT_COMMON_REFERENCE,)
    available_set = set(available_paths)
    required = [path for path in configured if path in available_set]
    if required:
        return required
    # 配置未命中任何现有文件时退回启发式，避免返回空清单
    return _select_references_by_heuristic(section_id=section_id, available_paths=available_paths)


class SkillReferenceContext(ReferenceContextPort):
    """基于 skill.infrastructure.selector 的参考文档上下文选择。

    选择策略（2026-09-21 调整）：
    - **必加载优先**：``INCIDENT_REPORT_SECTION_REFERENCE_MAP`` 定义的写作契约先占位；
    - **规划器只补充**：规划器的结果只能在剩余预算内追加，不再整体覆盖启发式；
    - **启发式兜底**：连接规划失败时，用文件名匹配补齐预算。
    """

    async def resolve(
        self,
        *,
        model: str,
        section_id: str,
        timeline_index: int | None,
        prompt: str,
        context_json: str,
    ) -> tuple[str, list[str], str]:
        reference_catalog = _build_incident_reference_catalog()
        available_paths = [item["path"] for item in reference_catalog]
        if not available_paths:
            return "[fallback]\n未找到可用参考文档，按上下文生成。", [], "fallback:no_reference_catalog"

        system_reference_skill_id = "__incident_reference_system__"

        required_files = _required_reference_files(
            section_id=section_id,
            available_paths=available_paths,
        )
        selected_files = list(required_files)
        selection_reason = f"required:section_contract({len(required_files)})"
        budget = max(0, INCIDENT_REPORT_REFERENCE_SELECT_LIMIT - len(selected_files))

        heuristic_files = _select_references_by_heuristic(
            section_id=section_id,
            available_paths=available_paths,
        )

        if budget > 0:
            try:
                planner_query = _build_reference_planner_query(
                    section_id=section_id,
                    timeline_index=timeline_index,
                    prompt=prompt,
                    context_json=context_json,
                    skill_markdown=_load_incident_skill_markdown(),
                )
                plan_decision = await select_for_workspace_reference(
                    model=model,
                    messages=[{"role": "user", "content": planner_query}],
                    available_skills=build_selector_skill_interfaces(
                        options=_build_reference_selector_options(reference_catalog),
                        skill_type="workspace_incident_reference",
                    ),
                    explicit_skill_ids=required_files,
                    system_skill_id=system_reference_skill_id,
                    reference_select_limit=INCIDENT_REPORT_REFERENCE_SELECT_LIMIT,
                    min_confidence=0.2,
                )
                for path in _select_reference_files_from_plan(
                    decision=plan_decision,
                    available_paths=available_paths,
                    system_skill_id=system_reference_skill_id,
                ):
                    if budget <= 0:
                        break
                    if path not in selected_files:
                        selected_files.append(path)
                        budget -= 1
                planner_reason = normalize_text(plan_decision.reasons.get("planner"))
                if planner_reason:
                    selection_reason = f"{selection_reason} | planner:{planner_reason}"
            except Exception as exc:
                selection_reason = f"{selection_reason} | planner_fallback:{summarize_exception(exc)}"

        # 剩余预算用启发式补齐，保证确定性匹配不被浪费
        if budget > 0:
            for path in heuristic_files:
                if budget <= 0:
                    break
                if path not in selected_files:
                    selected_files.append(path)
                    budget -= 1

        blocks: list[str] = []
        for relative_path in selected_files:
            text = _load_text_file(INCIDENT_REPORT_REFERENCE_DIR / relative_path)
            if not text:
                continue
            blocks.append(f"[{relative_path}]\n{text}")
        if not blocks:
            return "[fallback]\n参考文档为空，按上下文生成。", selected_files, selection_reason
        return "\n\n".join(blocks), selected_files, selection_reason


def _resolve_system_domain(data: Any) -> str:
    """从上下文字典里解析事故所属系统域。

    表单的 ``manual_system`` 是唯一结构化、可靠的检索键：
    它比从口语文本里正则抽取 token 稳定得多，且能避免跨域召回
    （数据库事故不应命中存储域的因果链）。
    """
    if not isinstance(data, dict):
        return ""
    cover = data.get("manual_cover_context")
    candidates: list[str] = []
    if isinstance(cover, dict):
        for key in ("system", "site_id", "location", "fault_symptom"):
            value = cover.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip().lower())
    system_value = data.get("system")
    if isinstance(system_value, str) and system_value.strip():
        candidates.append(system_value.strip().lower())

    for candidate in candidates:
        for _domain, (query_term, keywords) in INCIDENT_SYSTEM_DOMAIN_MAP.items():
            for keyword in keywords:
                if keyword in candidate:
                    return query_term
    return ""


def _build_retrieval_query(*, section_id: str, context_json: str) -> str:
    """构造检索 query：系统域 + 章节主题词 + ASCII 实体。

    2026-09-21 调整：原先只从 context_json 正则抽 ASCII token，中文口语输入
    几乎抽不出内容，query 退化为纯主题词，检索结果与本次事故无关。
    现在优先用表单 system 字段解析出的系统域定位语料范围。

    设计约束：
    - query 以英文短语为主，中文内容不直接进 query；
    - 系统域命中时形如 ``database incident impact quantification``；
    - 未命中系统域时退回主题词，并保留 ASCII 实体作为补充。
    """
    section = (section_id or "").strip().lower()
    topic_map = {
        "quick": "incident report structure overview key facts checklist",
        "impact": "incident impact affected service business disruption transaction count quantification",
        "root_cause": "root cause causal chain failure mode analysis",
        "follow_up": "remediation recovery action preventive measure checklist",
    }
    query = topic_map.get(section, "incident report accident analysis")

    try:
        data = json.loads(context_json) if isinstance(context_json, str) else context_json
    except Exception:
        return query

    domain = _resolve_system_domain(data)
    if domain:
        query = f"{domain} {query}"

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            for token in re.findall(r"[A-Za-z][A-Za-z0-9][A-Za-z0-9_/.\-]*", node):
                low = token.lower()
                if low in {"none", "n/a", "na", "null", "true", "false"}:
                    continue
                tokens.append(token)

    tokens: list[str] = []
    try:
        walk(data)
    except Exception:
        return query

    seen: set[str] = set()
    picked: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        picked.append(token)
        if len(picked) >= 8:
            break
    if picked:
        query = f"{query} " + " ".join(picked)
    return query


# 注入素材时的用途声明。
#
# 背景：知识库素材描述的是**其他事故**。不加声明时，模型会把历史报告里的
# 设备编号、时间戳、交易笔数、人名、版本号直接抄进新报告 —— 产出一份
# "数据翔实但全是假的"报告，比老实写 N/A 危险得多。
# 这条声明与 generation.py 的 _MATERIAL_SAFETY_RULES 是同一道护栏的两端：
# 一段贴在素材上，一段写进 system prompt。
_MATERIAL_USAGE_NOTICE = (
    "[RAGFlow reference material — structure and terminology reference only]\n"
    "The material below comes from OTHER incidents. Use it only as a guide to "
    "structure, terminology and level of detail. Never copy device identifiers, "
    "timestamps, counts, personnel names or version numbers from it. "
    "Every fact must come from the current context; write N/A when unavailable."
)


class CompositeReferenceContext(ReferenceContextPort):
    """本地规范(Standard) + RAGFlow 素材(Material) 组合参考上下文。

    对外契约与 SkillReferenceContext 完全一致（返回 (text, files, reason)）。
    仅在 quick/impact/root_cause/follow_up 四个 section 启用知识增强；
    description 和 timeline 是纯事实章节，注入素材会诱导编造，必须跳过。
    任何异常 → 降级返回 base 的结果，绝不阻断报告生成。
    """

    def __init__(
        self,
        *,
        base: ReferenceContextPort,
        retriever: KnowledgeRetrieverPort,
        ragflow_enabled_sections: str = "quick,impact,root_cause,follow_up",
        ragflow_top_k: int = 3,
    ) -> None:
        self._base = base
        self._retriever = retriever
        self._enabled_sections = {s.strip().lower() for s in (ragflow_enabled_sections or "").split(",") if s.strip()}
        self._top_k = ragflow_top_k

    async def resolve(
        self,
        *,
        model: str,
        section_id: str,
        timeline_index: int | None,
        prompt: str,
        context_json: str,
    ) -> tuple[str, list[str], str]:
        base_text = "[fallback]\nReference documentation unavailable, generate from context."
        base_files: list[str] = []
        base_reason = "fallback:init"
        try:
            base_text, base_files, base_reason = await self._base.resolve(
                model=model,
                section_id=section_id,
                timeline_index=timeline_index,
                prompt=prompt,
                context_json=context_json,
            )
        except Exception as exc:
            logger.warning("Base reference resolve failed, use empty base: %s", exc)

        section_key = (section_id or "").strip().lower()
        if section_key not in self._enabled_sections:
            return base_text, base_files, base_reason

        try:
            query = _build_retrieval_query(section_id=section_id, context_json=context_json)
            chunks = await self._retriever.retrieve(query=query, scope="history", top_k=self._top_k)
        except Exception as exc:
            logger.warning("Knowledge retrieval failed, degrade to base: %s", exc)
            return base_text, base_files, f"{base_reason} | ragflow:error:{type(exc).__name__}"

        if not chunks:
            return base_text, base_files, f"{base_reason} | ragflow:no_hits"

        material_header = _MATERIAL_USAGE_NOTICE
        material_blocks = [f"[RAGFlow · {chunk.source}]\n{chunk.content}" for chunk in chunks]
        combined = base_text + "\n\n" + material_header + "\n\n" + "\n\n".join(material_blocks)
        reason = f"{base_reason} | ragflow:{len(chunks)} chunks (scope=history)"
        return combined, base_files, reason
