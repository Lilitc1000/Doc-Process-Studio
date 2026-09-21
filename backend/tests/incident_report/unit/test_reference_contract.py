"""规范必加载契约测试。

背景（2026-09-21 修复）：
参考文档原先完全交给 LLM 规划器挑选，且规划器一旦返回多于显式项的结果，
就会**整体覆盖**启发式的确定性匹配。实测后果是 quick 模式（需要一次生成
全部字段）只加载 common.md(10 行) 与 quick-mode.md(16 行)，
而最详细的 impact.md / root-cause.md / follow-up.md 进不了 prompt，
导致同一份报告两次生成质量不同。

这里固化新行为：section 与规范文件硬绑定，规划器只能补充、不能覆盖。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

import doc_process_studio.incident_report.infrastructure.adapters.reference_context as reference_module
from doc_process_studio.incident_report.infrastructure.adapters.reference_context import (
    SkillReferenceContext,
    _required_reference_files,
)
from doc_process_studio.incident_report.infrastructure.utils.generation import (
    _build_body_generation_messages,
)
from doc_process_studio.skill.application.dtos.runtime import SkillPlanDecision

ALL_PATHS = [
    "body-sections/common.md",
    "body-sections/quick-mode.md",
    "body-sections/description.md",
    "body-sections/timeline.md",
    "body-sections/timeline-item.md",
    "body-sections/impact.md",
    "body-sections/root-cause.md",
    "body-sections/follow-up.md",
]


def _install_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reference_module,
        "_build_incident_reference_catalog",
        lambda: [{"path": p, "title": p, "summary": p} for p in ALL_PATHS],
    )
    monkeypatch.setattr(
        reference_module,
        "_load_text_file",
        lambda path: f"Content of {path.name}" if hasattr(path, "name") else "Reference",
    )


def _install_planner(
    monkeypatch: pytest.MonkeyPatch,
    active_skill_ids: list[str],
) -> None:
    # 桩函数忽略入参：下划线前缀让 ruff 的 ARG001 不把它当成漏用的参数
    async def fake_select(**_kwargs: Any) -> Any:
        return SkillPlanDecision(
            planner_model="m",
            required_skill_ids=[],
            optional_skill_ids=list(active_skill_ids),
            missing_explicit_skill_ids=[],
            active_skill_ids=list(active_skill_ids),
            primary_skill_id=active_skill_ids[0] if active_skill_ids else "",
            confidence=0.9,
            reasons={"planner": "planner:fake"},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(reference_module, "select_for_workspace_reference", fake_select)


def test_quick_mode_loads_all_detailed_contracts() -> None:
    """quick 一次生成全部字段，必须带上三份最详细的章节契约。"""
    required = _required_reference_files(section_id="quick", available_paths=ALL_PATHS)
    assert "body-sections/impact.md" in required
    assert "body-sections/root-cause.md" in required
    assert "body-sections/follow-up.md" in required
    assert "body-sections/common.md" in required


def test_section_specific_contract_is_narrow() -> None:
    """单章节只加载对应契约，不把无关规范塞进 prompt。"""
    required = _required_reference_files(section_id="impact", available_paths=ALL_PATHS)
    assert required == ["body-sections/common.md", "body-sections/impact.md"]


def test_unknown_section_falls_back_to_common() -> None:
    required = _required_reference_files(section_id="unknown_section", available_paths=ALL_PATHS)
    assert required, "未知 section 不应返回空清单"


async def test_planner_cannot_override_required_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """规划器返回无关文件时，必加载项仍必须保留。"""
    _install_catalog(monkeypatch)
    # 规划器故意只挑一个与 impact 无关的文件
    _install_planner(monkeypatch, ["body-sections/description.md"])

    context = SkillReferenceContext()
    _text, selected_files, reason = await context.resolve(
        model="m",
        section_id="impact",
        timeline_index=None,
        prompt="Generate impact",
        context_json="{}",
    )
    assert "body-sections/impact.md" in selected_files, "必加载契约被规划器覆盖了"
    assert "body-sections/common.md" in selected_files
    assert reason.startswith("required:section_contract")


async def test_quick_mode_selection_is_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    """同样的输入多次解析，结果必须一致（消除概率性加载）。"""
    _install_catalog(monkeypatch)
    _install_planner(monkeypatch, ["body-sections/description.md"])

    context = SkillReferenceContext()
    results = []
    for _ in range(3):
        _text, selected_files, _reason = await context.resolve(
            model="m",
            section_id="quick",
            timeline_index=None,
            prompt="Generate all",
            context_json="{}",
        )
        results.append(tuple(sorted(selected_files)))
    assert len(set(results)) == 1, f"多次解析结果不一致: {set(results)}"
    for required in (
        "body-sections/impact.md",
        "body-sections/root-cause.md",
        "body-sections/follow-up.md",
    ):
        assert required in results[0]


def test_system_prompt_contains_material_safety_rules() -> None:
    """system prompt 必须携带「素材不得照抄」护栏。"""
    messages = _build_body_generation_messages(
        prompt="p",
        context_json="{}",
        reference_context="[RAGFlow] NAS2 40,418",
    )
    system_content = messages[0]["content"]
    assert "Never copy device identifiers" in system_content
    assert "OTHER incidents" in system_content
