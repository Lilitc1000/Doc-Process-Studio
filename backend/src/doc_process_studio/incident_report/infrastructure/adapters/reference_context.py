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
    INCIDENT_REPORT_REFERENCE_DIR,
    INCIDENT_REPORT_REFERENCE_SELECT_LIMIT,
    INCIDENT_REPORT_SKILL_MD_PATH,
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


class SkillReferenceContext(ReferenceContextPort):
    """基于 skill.infrastructure.selector 的参考文档上下文选择。"""

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
        explicit_reference_paths: list[str] = []
        if "body-sections/common.md" in available_paths:
            explicit_reference_paths.append("body-sections/common.md")

        selection_reason = "fallback:heuristic"
        selected_files = _select_references_by_heuristic(
            section_id=section_id,
            available_paths=available_paths,
        )

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
                explicit_skill_ids=explicit_reference_paths,
                system_skill_id=system_reference_skill_id,
                reference_select_limit=INCIDENT_REPORT_REFERENCE_SELECT_LIMIT,
                min_confidence=0.2,
            )
            selected_from_plan = _select_reference_files_from_plan(
                decision=plan_decision,
                available_paths=available_paths,
                system_skill_id=system_reference_skill_id,
            )
            if selected_from_plan:
                if len(selected_from_plan) <= len(explicit_reference_paths):
                    merged_files = list(selected_from_plan)
                    for path in selected_files:
                        if path in merged_files:
                            continue
                        merged_files.append(path)
                        if len(merged_files) >= INCIDENT_REPORT_REFERENCE_SELECT_LIMIT:
                            break
                    selected_files = merged_files
                else:
                    selected_files = selected_from_plan
            planner_reason = normalize_text(plan_decision.reasons.get("planner"))
            selection_reason = planner_reason or "planner:select_for_workspace_reference"
        except Exception as exc:
            selection_reason = f"fallback:{summarize_exception(exc)}"

        blocks: list[str] = []
        for relative_path in selected_files:
            text = _load_text_file(INCIDENT_REPORT_REFERENCE_DIR / relative_path)
            if not text:
                continue
            blocks.append(f"[{relative_path}]\n{text}")
        if not blocks:
            return "[fallback]\n参考文档为空，按上下文生成。", selected_files, selection_reason
        return "\n\n".join(blocks), selected_files, selection_reason


def _build_retrieval_query(*, section_id: str, context_json: str) -> str:
    """从 context_json 构造英文检索 query。

    设计约束（来自交接文档）：
    - query 必须是英文短语，不要直接把用户填的中文丢进去；
    - 仅抽取 ASCII 实体（设备号 / 系统名等），中文内容不参与；
    - 叠加 section 维度的英文主题词，引导检索命中对应素材块。
    """
    section = (section_id or "").strip().lower()
    topic_map = {
        "quick": "incident report overview summary key facts",
        "impact": "incident impact affected service business disruption transaction data loss",
        "root_cause": "root cause failure NAS storage HA failover NFS IO overload",
        "follow_up": "remediation recovery action fix recommendation preventive measure",
    }
    query = topic_map.get(section, "incident report accident analysis")

    try:
        data = json.loads(context_json) if isinstance(context_json, str) else context_json
    except Exception:
        return query

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

        material_blocks = [f"[RAGFlow {chunk.source}]\n{chunk.content}" for chunk in chunks]
        combined = base_text + "\n\n" + "\n\n".join(material_blocks)
        reason = f"{base_reason} | ragflow:{len(chunks)} chunks (scope=history)"
        return combined, base_files, reason
