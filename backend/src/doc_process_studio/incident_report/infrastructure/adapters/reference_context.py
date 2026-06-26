"""参考文档上下文选择端口实现。

封装 skill.infrastructure.selector 的跨域调用。
本模块位于 infrastructure 层，可直接调用跨域服务。
"""

import json
import logging
import re
from pathlib import Path

from ....common.utils.error_utils import summarize_exception
from ....skill.application.dtos.runtime import SkillPlanDecision
from ....skill.infrastructure.selector import (
    SelectorOption,
    build_selector_skill_interfaces,
    select_for_workspace_reference,
)
from ...application.ports import ReferenceContextPort
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
