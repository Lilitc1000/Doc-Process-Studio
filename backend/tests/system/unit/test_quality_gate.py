import json
from pathlib import Path

from doc_process_studio.chat.schemas.request import ChatMessageInput
from doc_process_studio.skill.models.catalog import SkillInterfaceConfig
from doc_process_studio.system.service.quality_gate import (
    QualityGateThresholds,
    QualityMetrics,
    compute_tool_metrics_from_traces,
    evaluate_quality_gate,
)
from doc_process_studio.skill.service.planner import build_implicit_skill_candidates


def _build_skills() -> list[SkillInterfaceConfig]:
    return [
        SkillInterfaceConfig(
            id="document-assistant",
            display_name="文档处理助手",
            short_description="阅读并整理 PDF/Word/Excel/PPT 等文档",
            default_prompt="doc",
            tools=[],
        ),
        SkillInterfaceConfig(
            id="resume-transport-review",
            display_name="交通简历审核",
            short_description="审核候选人是否具备交通行业经验",
            default_prompt="resume",
            tools=[],
        ),
        SkillInterfaceConfig(
            id="project-architecture-docx",
            display_name="架构文档生成",
            short_description="读取项目并生成架构设计 DOCX",
            default_prompt="arch",
            tools=[],
        ),
        SkillInterfaceConfig(
            id="incident-report",
            display_name="事故报告生成",
            short_description="收集事故信息并生成事故报告文档",
            default_prompt="incident",
            tools=[],
        ),
    ]


def test_skill_selection_precision_gate_from_benchmark_cases() -> None:
    dataset_path = Path(__file__).resolve().parent / "skill_selection_cases.json"
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    skills = _build_skills()

    matched = 0
    for case in cases:
        query = str(case["query"])
        expected = str(case["expected_primary_skill"])
        candidates = build_implicit_skill_candidates(
            messages=[ChatMessageInput(role="user", content=query)],
            available_skills=skills,
            explicit_skill_ids=[],
            system_skill_id="document-assistant",
            top_k=3,
        )
        predicted = candidates[0][0] if candidates else "document-assistant"
        if predicted == expected:
            matched += 1

    precision = matched / len(cases)
    assert precision >= 0.85


def test_quality_gate_blocks_release_when_metric_below_threshold() -> None:
    metrics = QualityMetrics(
        skill_selection_precision=0.80,
        tool_success_rate=0.95,
        first_response_latency_ms=1200,
        invalid_tool_call_rate=0.05,
        user_interrupt_rate=0.10,
    )
    failures = evaluate_quality_gate(
        metrics=metrics,
        thresholds=QualityGateThresholds(min_skill_selection_precision=0.85),
    )
    assert any("skill_selection_precision" in failure for failure in failures)


def test_compute_tool_metrics_from_traces() -> None:
    trace_payloads = [
        {
            "events": [
                {"type": "first_assistant_chunk", "detail": {"latency_ms": 1200}},
            ],
            "rounds": [
                {
                    "tool_trace_messages": [
                        {"role": "tool", "content": '{"ok": true}'},
                        {"role": "tool", "content": '{"ok": false, "error": "参数错误"}'},
                    ]
                }
            ],
            "final": {"error": ""},
        }
    ]
    metrics = compute_tool_metrics_from_traces(trace_payloads)
    assert metrics["tool_success_rate"] == 0.5
    assert metrics["invalid_tool_call_rate"] == 0.5
    assert metrics["first_response_latency_ms"] == 1200


def test_quality_gate_passes_when_all_metrics_reach_threshold() -> None:
    metrics = QualityMetrics(
        skill_selection_precision=0.90,
        tool_success_rate=0.95,
        first_response_latency_ms=1600,
        invalid_tool_call_rate=0.08,
        user_interrupt_rate=0.12,
    )
    failures = evaluate_quality_gate(
        metrics=metrics,
        thresholds=QualityGateThresholds(
            min_skill_selection_precision=0.85,
            min_tool_success_rate=0.90,
            max_first_response_latency_ms=3000,
            max_invalid_tool_call_rate=0.15,
            max_user_interrupt_rate=0.30,
        ),
    )
    assert failures == []
