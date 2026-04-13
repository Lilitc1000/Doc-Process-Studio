import json
from dataclasses import dataclass
from typing import Any


@dataclass
class QualityMetrics:
    skill_selection_precision: float
    tool_success_rate: float
    first_response_latency_ms: float
    invalid_tool_call_rate: float
    user_interrupt_rate: float


@dataclass
class QualityGateThresholds:
    min_skill_selection_precision: float = 0.85
    min_tool_success_rate: float = 0.90
    max_first_response_latency_ms: float = 4_000
    max_invalid_tool_call_rate: float = 0.15
    max_user_interrupt_rate: float = 0.35


def evaluate_quality_gate(
    *,
    metrics: QualityMetrics,
    thresholds: QualityGateThresholds,
) -> list[str]:
    failures: list[str] = []
    if metrics.skill_selection_precision < thresholds.min_skill_selection_precision:
        failures.append(
            "skill_selection_precision"
            f"={metrics.skill_selection_precision:.3f} < {thresholds.min_skill_selection_precision:.3f}"
        )
    if metrics.tool_success_rate < thresholds.min_tool_success_rate:
        failures.append(
            f"tool_success_rate={metrics.tool_success_rate:.3f} < {thresholds.min_tool_success_rate:.3f}"
        )
    if metrics.first_response_latency_ms > thresholds.max_first_response_latency_ms:
        failures.append(
            "first_response_latency_ms"
            f"={metrics.first_response_latency_ms:.1f} > {thresholds.max_first_response_latency_ms:.1f}"
        )
    if metrics.invalid_tool_call_rate > thresholds.max_invalid_tool_call_rate:
        failures.append(
            "invalid_tool_call_rate"
            f"={metrics.invalid_tool_call_rate:.3f} > {thresholds.max_invalid_tool_call_rate:.3f}"
        )
    if metrics.user_interrupt_rate > thresholds.max_user_interrupt_rate:
        failures.append(
            f"user_interrupt_rate={metrics.user_interrupt_rate:.3f} > {thresholds.max_user_interrupt_rate:.3f}"
        )
    return failures


def compute_tool_metrics_from_traces(
    trace_payloads: list[dict[str, Any]],
) -> dict[str, float]:
    total_calls = 0
    success_calls = 0
    invalid_calls = 0
    latency_values: list[float] = []
    interrupted_requests = 0

    for payload in trace_payloads:
        events = payload.get("events")
        if isinstance(events, list):
            for event in events:
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "first_assistant_chunk":
                    detail = event.get("detail")
                    if isinstance(detail, dict):
                        latency = detail.get("latency_ms")
                        if isinstance(latency, (int, float)):
                            latency_values.append(float(latency))

        rounds = payload.get("rounds")
        if isinstance(rounds, list):
            for round_item in rounds:
                if not isinstance(round_item, dict):
                    continue
                tool_trace_messages = round_item.get("tool_trace_messages")
                if not isinstance(tool_trace_messages, list):
                    continue
                for message in tool_trace_messages:
                    if not isinstance(message, dict):
                        continue
                    if message.get("role") != "tool":
                        continue
                    total_calls += 1
                    content = message.get("content")
                    if not isinstance(content, str):
                        continue
                    try:
                        parsed = json.loads(content)
                    except json.JSONDecodeError:
                        invalid_calls += 1
                        continue
                    if bool(parsed.get("ok")):
                        success_calls += 1
                    error_message = str(parsed.get("error", "")).strip().lower()
                    if any(keyword in error_message for keyword in ["未知工具", "参数", "invalid", "schema"]):
                        invalid_calls += 1

        final = payload.get("final")
        if isinstance(final, dict):
            error = str(final.get("error", "")).strip()
            if "已停止输出" in error:
                interrupted_requests += 1

    tool_success_rate = (success_calls / total_calls) if total_calls > 0 else 1.0
    invalid_tool_call_rate = (invalid_calls / total_calls) if total_calls > 0 else 0.0
    first_response_latency_ms = (
        sum(latency_values) / len(latency_values) if latency_values else 0.0
    )
    user_interrupt_rate = (
        interrupted_requests / len(trace_payloads) if trace_payloads else 0.0
    )
    return {
        "tool_success_rate": tool_success_rate,
        "invalid_tool_call_rate": invalid_tool_call_rate,
        "first_response_latency_ms": first_response_latency_ms,
        "user_interrupt_rate": user_interrupt_rate,
    }
