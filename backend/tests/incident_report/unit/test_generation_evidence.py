"""生成提示词「证据意识」约束的单元测试。

覆盖 generation.py 的 5 处 prompt 注入点：
  system prompt（全章节）/ quick / impact / root_cause / follow_up

并断言 description、timeline 这类纯事实章节**不会**被注入分段专属规则。
"""

from typing import Any

import pytest

import doc_process_studio.incident_report.infrastructure.utils.generation as generation_module
from doc_process_studio.incident_report.application.dtos import IncidentFormSnapshot

VAGUE_WORDS = ("significantly", "severely", "considerably", "substantially", "to some extent")
BLACKBOX_LABELS = ("hardware issue", "system error", "unknown reason")
FOLLOW_UP_BANNED = ("will follow up", "monitor the situation", "improve stability")


def _make_snapshot(**overrides: Any) -> IncidentFormSnapshot:
    defaults: dict[str, Any] = dict(form_answers={}, report_data=None)
    defaults.update(overrides)
    return IncidentFormSnapshot(**defaults)


def _section_prompt(section_id: str) -> str:
    prompt, _context = generation_module._build_section_generation_prompt(
        _make_snapshot(),
        section_id=section_id,
        timeline_index=None,
    )
    return prompt


def test_evidence_rules_constants_declared() -> None:
    """四个规则常量必须存在，避免后续重构时被误删而静默失效。"""
    for name in (
        "_EVIDENCE_RULES_COMMON",
        "_EVIDENCE_RULES_IMPACT",
        "_EVIDENCE_RULES_ROOT_CAUSE",
        "_EVIDENCE_RULES_FOLLOW_UP",
    ):
        assert hasattr(generation_module, name), f"missing constant: {name}"


def test_common_rules_ban_vague_intensifiers() -> None:
    text = generation_module._EVIDENCE_RULES_COMMON.lower()
    for word in VAGUE_WORDS:
        assert word in text, f"missing banned intensifier: {word}"


def test_common_rules_require_na_instead_of_fabrication() -> None:
    text = generation_module._EVIDENCE_RULES_COMMON
    assert "N/A" in text
    assert "never fabricate" in text


def test_system_prompt_carries_common_rules() -> None:
    messages = generation_module._build_body_generation_messages(prompt="p", context_json="{}", reference_context="r")
    system_content = messages[0]["content"]
    assert "never fabricate" in system_content
    assert "significantly" in system_content.lower()


def test_quick_prompt_carries_all_rules() -> None:
    prompt, _context = generation_module._build_quick_generation_request(_make_snapshot())
    assert "Evidence rules" in prompt
    assert "Impact rules" in prompt
    assert "Root cause rules" in prompt
    assert "Follow-up rules" in prompt


@pytest.mark.parametrize(
    ("section_id", "marker"),
    [
        ("impact", "Impact rules"),
        ("root_cause", "Root cause rules"),
        ("follow_up", "Follow-up rules"),
    ],
)
def test_section_prompt_carries_own_rules(section_id: str, marker: str) -> None:
    prompt = _section_prompt(section_id)
    assert marker in prompt
    assert "Evidence rules" in prompt


def test_fact_sections_exclude_specific_rules() -> None:
    """description / timeline 是纯事实章节，注入素材规则会诱导编造。"""
    for section_id in ("description", "timeline"):
        prompt = _section_prompt(section_id)
        assert "Impact rules" not in prompt, f"{section_id} 被污染"
        assert "Root cause rules" not in prompt, f"{section_id} 被污染"
        assert "Follow-up rules" not in prompt, f"{section_id} 被污染"


def test_impact_rules_require_device_timestamp_and_business_action() -> None:
    text = generation_module._EVIDENCE_RULES_IMPACT.lower()
    assert "device" in text
    assert "hh:mm" in text
    assert "business action" in text


def test_root_cause_rules_ban_blackbox_labels() -> None:
    text = generation_module._EVIDENCE_RULES_ROOT_CAUSE.lower()
    for label in BLACKBOX_LABELS:
        assert label in text, f"missing black-box label: {label}"


def test_follow_up_rules_ban_vague_actions() -> None:
    text = generation_module._EVIDENCE_RULES_FOLLOW_UP.lower()
    for phrase in FOLLOW_UP_BANNED:
        assert phrase in text, f"missing banned phrase: {phrase}"


def test_evidence_rules_do_not_break_json_contract() -> None:
    """补规则不能破坏原有的输出 JSON 约定。"""
    prompt, _ = generation_module._build_section_generation_prompt(
        _make_snapshot(), section_id="impact", timeline_index=None
    )
    for key in ("body_impact_scope", "body_impact_severity", "body_business_impact"):
        assert key in prompt


def test_root_cause_rules_require_minimum_chain_length() -> None:
    """回归：只要求'不要编造'会让模型把链条压缩成一句话。"""
    text = generation_module._EVIDENCE_RULES_ROOT_CAUSE.lower()
    assert "at least 3" in text, "缺少链条最少环数约束"
    assert "one or two sentences is not an analysis" in text


def test_root_cause_rules_prefer_inferred_over_na() -> None:
    """回归：N/A 被当成默认出路，导致证据不足时整段退化。"""
    text = generation_module._EVIDENCE_RULES_ROOT_CAUSE.lower()
    assert "inferred" in text, "缺少 inferred 分层标注机制"
    assert "even inference is impossible" in text, "未限定 N/A 为最后手段"


def test_follow_up_rules_require_both_action_types_and_minimum_count() -> None:
    """回归：整改清单被压缩到 2~3 条，且只剩短期止血。"""
    text = generation_module._EVIDENCE_RULES_FOLLOW_UP.lower()
    assert "at least 4" in text, "缺少条数下限"
    assert "short-term recovery" in text, "缺少短期止血要求"
    assert "long-term prevention" in text, "缺少长期治理要求"


def test_follow_up_rules_keep_action_when_fields_missing() -> None:
    """信息不足时压缩的是字段，不是条数。"""
    text = generation_module._EVIDENCE_RULES_FOLLOW_UP.lower()
    assert "instead of dropping the action" in text
