import asyncio
import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx

from ...models.conversation.incident_report import (
    IncidentFormAnswer,
    IncidentReportFormSchemaResponse,
    IncidentReportGenerateResponse,
    IncidentReportSessionDetail,
    IncidentReportSessionListResponse,
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
    build_empty_incident_snapshot,
)
from ...models.conversation.stream import ChatMessageInput, ChatStreamRequest
from ...models.skill.interaction import SkillInteractionConfig, SkillInteractionStep
from ...models.skill.runtime import SkillConversationState
from ...services.agent.error_detail import build_exception_detail, summarize_exception
from ...services.infra.dtutils import utcnow
from ...services.infra.error_utils import build_error_event_detail
from ...services.infra.text_utils import parse_json_object
from ...services.infra.tool_args import (
    build_normalized_tool_calls,
    extract_tool_name,
    parse_tool_arguments,
)
from ...services.agent.trace_store import (
    AgentTraceRecorder,
    delete_agent_traces_for_conversation,
)
from ...settings import settings
from ..infra.ollama_client import stream_chat_completion
from ..skill.conversation_store import clear_conversation_state
from ..skill.registry import get_skill_interaction_config, get_skill_interface
from ..skill.tool_loop import build_skill_tools, execute_skill_tool_call
from .attachments import delete_attachments_for_conversation, save_uploaded_attachment
from .incident_session_store import (
    delete_incident_session_records,
    list_incident_session_ids,
    load_incident_session_snapshot,
    load_incident_session_summary,
    save_incident_session_snapshot,
    save_incident_session_summary,
    touch_incident_session_index,
)
from .file_context import build_persisted_uploaded_files_context
from .streaming import (
    build_upstream_messages_for_skills,
    extract_delta_text,
    extract_delta_tool_calls,
    extract_done_reason,
    merge_stream_tool_calls,
)

INCIDENT_REPORT_SKILL_ID = "incident-report"
INCIDENT_REPORT_DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
INCIDENT_REPORT_GENERATE_MESSAGE_ID = "incident-report-generate"
INCIDENT_REPORT_INPUT_FILE_NAME = "incident_data.json"

def _is_docx_attachment(attachment: Any) -> bool:
    attachment_name = str(getattr(attachment, "name", "")).strip().lower()
    attachment_mime = str(getattr(attachment, "mime_type", "")).strip().lower()
    return attachment_name.endswith(".docx") and (
        attachment_mime == INCIDENT_REPORT_DOCX_MIME_TYPE
    )


def _build_default_title(now: datetime | None = None) -> str:
    current = now or utcnow()
    return f"事故报告-{current.strftime('%Y/%m/%d %H:%M')}"


def _build_summary_from_detail(
    detail: IncidentReportSessionDetail,
    *,
    status: str | None = None,
    title: str | None = None,
    updated_at: datetime | None = None,
) -> IncidentReportSessionSummary:
    payload = detail.model_dump(exclude={"snapshot"})
    if status is not None:
        payload["status"] = status
    if title is not None:
        payload["title"] = title
    if updated_at is not None:
        payload["updated_at"] = updated_at
    return IncidentReportSessionSummary.model_validate(payload)

def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _format_local_datetime_text(value: str) -> str:
    normalized = value.strip()
    matched = re.match(r"^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})", normalized)
    if not matched:
        return normalized
    year, month, day, hour, minute = matched.groups()
    return f"{day}/{month}/{year} {hour}:{minute}"


def _set_nested_value(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    keys = [key.strip() for key in dotted_path.split(".") if key.strip()]
    if not keys:
        return

    current = target
    for key in keys[:-1]:
        node = current.get(key)
        if not isinstance(node, dict):
            node = {}
            current[key] = node
        current = node
    current[keys[-1]] = value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
            continue
        merged[key] = deepcopy(value)
    return merged


def _extract_answer_value(
    *,
    step: SkillInteractionStep,
    answer: IncidentFormAnswer | None,
) -> Any:
    if answer is None:
        if step.required:
            raise ValueError("缺少必填项")
        return ""

    if step.kind == "text":
        text_value = _normalize_text(answer.custom_value or answer.value)
        if text_value and step.id in {"start_time", "detected_time", "resolved_time"}:
            text_value = _format_local_datetime_text(text_value)
        if not text_value and step.required:
            raise ValueError("缺少必填项")
        return text_value

    if step.kind == "multi_select":
        raw_values = answer.value if isinstance(answer.value, list) else []
        values = [_normalize_text(item) for item in raw_values if _normalize_text(item)]
        if step.allow_custom:
            custom_value = _normalize_text(answer.custom_value)
            if custom_value:
                values.append(custom_value)
        if step.required and not values:
            raise ValueError("缺少必填项")
        if not step.allow_custom:
            declared_values = {option.value for option in step.options}
            invalid_values = [value for value in values if value not in declared_values]
            if invalid_values:
                raise ValueError("包含无效选项")
        return values

    single_value = _normalize_text(answer.custom_value or answer.value)
    if step.required and not single_value:
        raise ValueError("缺少必填项")
    if not single_value:
        return single_value

    declared_values = {option.value for option in step.options}
    if declared_values and single_value not in declared_values and not step.allow_custom:
        raise ValueError("包含无效选项")
    return single_value


def _build_report_data_from_snapshot(
    *,
    config: SkillInteractionConfig,
    snapshot: IncidentReportSessionSnapshot,
) -> tuple[dict[str, Any] | None, list[str]]:
    collected: dict[str, Any] = {}
    missing_fields: list[str] = []

    for step in config.steps:
        answer = snapshot.form_answers.get(step.id)
        try:
            answer_value = _extract_answer_value(step=step, answer=answer)
        except ValueError:
            missing_fields.append(step.title)
            continue

        if answer_value == "" and not step.required:
            continue
        _set_nested_value(collected, step.field_path, answer_value)

    if missing_fields:
        return None, missing_fields

    return _deep_merge(config.defaults, collected), []


async def _run_skill_chat_completion_round(
    *,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], str]:
    assistant_content_parts: list[str] = []
    merged_tool_calls: dict[int, dict[str, Any]] = {}
    done_reason = "stop"

    async for chunk_payload in stream_chat_completion(
        model=model,
        messages=messages,
        tools=tools,
    ):
        if chunk_payload is None:
            break

        delta_text = extract_delta_text(chunk_payload)
        if delta_text:
            assistant_content_parts.append(delta_text)

        delta_tool_calls = extract_delta_tool_calls(chunk_payload)
        if delta_tool_calls:
            merge_stream_tool_calls(merged_tool_calls, delta_tool_calls)

        chunk_done_reason = extract_done_reason(chunk_payload)
        if chunk_done_reason:
            done_reason = chunk_done_reason

    normalized_tool_calls = [
        merged_tool_calls[index] for index in sorted(merged_tool_calls.keys())
    ]
    return "".join(assistant_content_parts), normalized_tool_calls, done_reason


def _extract_report_data_from_tool_call(tool_call: dict[str, Any]) -> dict[str, Any] | None:
    arguments = parse_tool_arguments(tool_call)
    raw_report_data = arguments.get("report_data")
    if isinstance(raw_report_data, dict):
        return deepcopy(raw_report_data)
    if isinstance(raw_report_data, str):
        return parse_json_object(raw_report_data)
    return None


def _build_incident_generate_instruction(*, output_name: str) -> str:
    return (
        "请基于当前会话已上传的 incident_data.json 生成事故报告附件。"
        "先读取该文件内容，保持 JSON 键结构不变，只润色其中叙述型文本字段（如事件描述、故障现象、根因、影响描述、措施描述等）；"
        "不得编造事实，空值可补 N/A。"
        "润色完成后，必须调用 generate_incident_report 工具，"
        "并将润色后的完整 JSON 作为 report_data 传入。"
        f"输出文件名请使用：{output_name}"
    )


async def _flush_trace_safely(recorder: AgentTraceRecorder) -> None:
    try:
        await recorder.flush()
    except Exception:
        # trace 增量写入失败不应中断主流程。
        return


def _build_generate_output_name(
    *,
    session_title: str,
    output_name: str | None,
    session_id: str,
) -> str:
    if output_name and output_name.strip():
        return output_name.strip()
    normalized_title = session_title.strip().replace(" ", "-").replace("/", "-")
    if normalized_title:
        return f"{normalized_title}.docx"
    return f"incident-report-{session_id[:8]}.docx"


def _build_incident_interaction_config() -> SkillInteractionConfig:
    config = get_skill_interaction_config(INCIDENT_REPORT_SKILL_ID)
    if config is None:
        raise ValueError("incident-report 未配置 interaction.json，无法构建表单。")
    return config


async def list_incident_report_sessions() -> IncidentReportSessionListResponse:
    session_ids = await list_incident_session_ids()
    sessions: list[IncidentReportSessionSummary] = []
    for session_id in session_ids:
        summary = await load_incident_session_summary(session_id)
        if summary is not None:
            sessions.append(summary)
    return IncidentReportSessionListResponse(sessions=sessions)


async def get_incident_report_session(
    session_id: str,
) -> IncidentReportSessionDetail | None:
    summary = await load_incident_session_summary(session_id)
    snapshot = await load_incident_session_snapshot(session_id)
    if summary is None or snapshot is None:
        return None
    return IncidentReportSessionDetail(
        **summary.model_dump(),
        snapshot=snapshot,
    )


async def create_incident_report_session(
    *,
    title: str,
) -> IncidentReportSessionSummary:
    now = utcnow()
    session_id = uuid4().hex
    summary = IncidentReportSessionSummary(
        id=session_id,
        title=(title.strip() or _build_default_title(now)),
        status="draft",
        created_at=now,
        updated_at=now,
    )
    snapshot = build_empty_incident_snapshot()
    await save_incident_session_summary(summary)
    await save_incident_session_snapshot(session_id, snapshot)
    await touch_incident_session_index(session_id, now.timestamp())
    return summary


async def update_incident_report_session_snapshot(
    *,
    session_id: str,
    snapshot: IncidentReportSessionSnapshot,
) -> IncidentReportSessionDetail | None:
    existing = await get_incident_report_session(session_id)
    if existing is None:
        return None

    if existing.snapshot.is_locked:
        raise ValueError("附件已生成，当前会话已锁定，不能继续编辑。")

    now = utcnow()
    next_summary = _build_summary_from_detail(
        existing,
        status="draft",
        updated_at=now,
    )
    next_snapshot = IncidentReportSessionSnapshot(
        form_answers=snapshot.form_answers,
        report_data=None,
        generated_attachment=None,
        generated_trace_id=None,
        generated_at=None,
        is_locked=False,
        fallback_used=False,
        polish_error=None,
    )

    await save_incident_session_summary(next_summary)
    await save_incident_session_snapshot(session_id, next_snapshot)
    await touch_incident_session_index(session_id, now.timestamp())
    return IncidentReportSessionDetail(
        **next_summary.model_dump(),
        snapshot=next_snapshot,
    )


async def update_incident_report_session_title(
    *,
    session_id: str,
    title: str,
) -> IncidentReportSessionSummary | None:
    detail = await get_incident_report_session(session_id)
    if detail is None:
        return None
    now = utcnow()
    summary = _build_summary_from_detail(
        detail,
        title=title.strip(),
        updated_at=now,
    )
    await save_incident_session_summary(summary)
    await touch_incident_session_index(session_id, now.timestamp())
    return summary


async def _save_generation_failure(
    *,
    detail: IncidentReportSessionDetail,
    session_id: str,
    trace_id: str,
    recorder: AgentTraceRecorder,
    fallback_used: bool,
    polish_error: str | None,
    failure_message: str,
    done_reason: str,
    exc: BaseException | None = None,
) -> None:
    failed_at = utcnow()
    failed_summary = _build_summary_from_detail(
        detail,
        status="failed",
        updated_at=failed_at,
    )
    failed_snapshot = IncidentReportSessionSnapshot(
        form_answers=detail.snapshot.form_answers,
        report_data=None,
        generated_attachment=None,
        generated_trace_id=trace_id,
        generated_at=None,
        is_locked=False,
        fallback_used=fallback_used,
        polish_error=(polish_error or failure_message),
    )
    await save_incident_session_summary(failed_summary)
    await save_incident_session_snapshot(session_id, failed_snapshot)
    await touch_incident_session_index(session_id, failed_at.timestamp())
    error_detail = await build_error_event_detail(
        message=failure_message,
        exc=exc,
        extra={
            "ok": False,
            "error": failure_message,
            "fallback_used": fallback_used,
        },
    ) if exc is not None else {
        "ok": False,
        "error": failure_message,
        "fallback_used": fallback_used,
    }
    recorder.add_event(
        event_type="attachment_generated",
        detail=error_detail,
    )
    recorder.set_final(done_reason=done_reason, error=failure_message)
    await recorder.flush()


async def _execute_skill_generation_rounds(
    *,
    model: str,
    request: ChatStreamRequest,
    state: SkillConversationState,
    skill_tools: list[dict[str, Any]],
    uploaded_files_context: str,
    recorder: AgentTraceRecorder,
    max_rounds: int,
) -> tuple[list[Any], dict[str, Any]]:
    tool_trace_messages: list[dict[str, Any]] = []
    attachments: list[Any] = []
    final_report_data: dict[str, Any] | None = None

    for round_index in range(1, max_rounds + 1):
        upstream_messages = build_upstream_messages_for_skills(
            request=request,
            active_skill_ids=[INCIDENT_REPORT_SKILL_ID],
            explicit_skill_ids=[INCIDENT_REPORT_SKILL_ID],
            uploaded_files_context=uploaded_files_context,
            extra_messages=tool_trace_messages,
        )
        try:
            assistant_content, round_tool_calls, done_reason = await _run_skill_chat_completion_round(
                model=model,
                messages=upstream_messages,
                tools=skill_tools,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"incident-report skill 对话失败：{summarize_exception(exc)}"
            ) from exc
        native_tool_calls = build_normalized_tool_calls(round_tool_calls)
        if assistant_content or native_tool_calls:
            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_content,
            }
            if native_tool_calls:
                assistant_message["tool_calls"] = native_tool_calls
            tool_trace_messages.append(assistant_message)

        recorder.add_event(
            event_type="skill_chat_round",
            detail={
                "round": round_index,
                "tool_call_count": len(round_tool_calls),
                "assistant_has_content": bool(assistant_content.strip()),
                "done_reason": done_reason,
            },
        )
        await _flush_trace_safely(recorder)
        if not round_tool_calls:
            if attachments:
                break
            raise RuntimeError(
                "incident-report skill 未触发 generate_incident_report 工具调用。"
            )

        for tool_call in round_tool_calls:
            tool_name = extract_tool_name(tool_call)
            tool_result, next_attachments = execute_skill_tool_call(
                request=request,
                state=state,
                tool_call=tool_call,
            )
            tool_trace_messages.append(
                {
                    "role": "tool",
                    "name": tool_name or "unknown_tool",
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )
            if not tool_result.get("ok"):
                raise RuntimeError(str(tool_result.get("error", "生成附件失败。")))

            if tool_name == "generate_incident_report":
                polished_report_data = _extract_report_data_from_tool_call(tool_call)
                if polished_report_data is not None:
                    final_report_data = polished_report_data
            attachments.extend(next_attachments)

        if attachments:
            break

    if not attachments:
        raise RuntimeError("incident-report skill 对话结束后未生成任何附件。")

    docx_attachment = next(
        (item for item in attachments if _is_docx_attachment(item)),
        None,
    )
    if docx_attachment is None:
        raise RuntimeError("事故报告仅支持生成 DOCX 附件。")

    return attachments, final_report_data


async def generate_incident_report_session_attachment(
    *,
    session_id: str,
    model: str,
    reranker_model: str | None = None,
    output_name: str | None = None,
) -> IncidentReportGenerateResponse | None:
    detail = await get_incident_report_session(session_id)
    if detail is None:
        return None

    if detail.snapshot.is_locked and detail.snapshot.generated_attachment is not None:
        trace_id = detail.snapshot.generated_trace_id or ""
        return IncidentReportGenerateResponse(
            session=_build_summary_from_detail(detail),
            snapshot=detail.snapshot,
            trace_id=trace_id,
        )

    config = _build_incident_interaction_config()
    draft_report_data, missing_fields = _build_report_data_from_snapshot(
        config=config,
        snapshot=detail.snapshot,
    )
    if draft_report_data is None:
        raise ValueError(
            "以下必填项未完成：" + "、".join(missing_fields)
        )
    effective_reranker_model = (reranker_model or "").strip() or model

    trace_id = uuid4().hex
    recorder = AgentTraceRecorder(
        trace_id=trace_id,
        tenant_id="default",
        conversation_id=session_id,
        user_message_id="incident-report-generate",
        model=model,
        reranker_model=effective_reranker_model,
    )
    recorder.add_event(
        event_type="form_validation",
        detail={
            "ok": True,
            "step_count": len(config.steps),
        },
    )
    await _flush_trace_safely(recorder)

    now = utcnow()
    generating_summary = _build_summary_from_detail(
        detail,
        status="generating",
        updated_at=now,
    )
    await save_incident_session_summary(generating_summary)
    generating_snapshot = IncidentReportSessionSnapshot(
        form_answers=detail.snapshot.form_answers,
        report_data=None,
        generated_attachment=None,
        generated_trace_id=trace_id,
        generated_at=None,
        is_locked=False,
        fallback_used=False,
        polish_error=None,
    )
    await save_incident_session_snapshot(session_id, generating_snapshot)
    await touch_incident_session_index(session_id, now.timestamp())

    fallback_used = False
    polish_error: str | None = None

    try:
        if not settings.ollama_base_url:
            raise RuntimeError("未配置 OLLAMA_BASE_URL。")

        target_output_name = _build_generate_output_name(
            session_title=detail.title,
            output_name=output_name,
            session_id=session_id,
        )
        incident_data_text = json.dumps(
            draft_report_data,
            ensure_ascii=False,
            indent=2,
        )
        incident_data_attachment = save_uploaded_attachment(
            raw_bytes=incident_data_text.encode("utf-8"),
            conversation_id=session_id,
            skill_id=INCIDENT_REPORT_SKILL_ID,
            file_name=INCIDENT_REPORT_INPUT_FILE_NAME,
            mime_type="application/json",
            extracted_text=incident_data_text,
        )
        recorder.add_event(
            event_type="incident_data_uploaded",
            detail={
                "ok": True,
                "attachment_id": incident_data_attachment.attachment_id,
                "name": INCIDENT_REPORT_INPUT_FILE_NAME,
            },
        )
        await _flush_trace_safely(recorder)

        request = ChatStreamRequest(
            user_message_id=INCIDENT_REPORT_GENERATE_MESSAGE_ID,
            conversation_id=session_id,
            model=model,
            reranker_model=effective_reranker_model,
            skill_id=INCIDENT_REPORT_SKILL_ID,
            selected_skill_ids=[INCIDENT_REPORT_SKILL_ID],
            messages=[
                ChatMessageInput(
                    role="user",
                    content=_build_incident_generate_instruction(
                        output_name=target_output_name
                    ),
                )
            ],
            attachment_ids=[incident_data_attachment.attachment_id],
        )
        uploaded_files_context = build_persisted_uploaded_files_context(
            request.attachment_ids
        )
        if not uploaded_files_context:
            raise RuntimeError("incident_data.json 文件上下文构建失败。")

        state = SkillConversationState(
            conversation_id=session_id,
            skill_id=INCIDENT_REPORT_SKILL_ID,
            system_prompt=get_skill_interface(INCIDENT_REPORT_SKILL_ID).default_prompt,
        )

        skill_tools = build_skill_tools(INCIDENT_REPORT_SKILL_ID)
        max_rounds = max(1, settings.skill_tool_max_iterations)
        attachments, final_report_data = await _execute_skill_generation_rounds(
            model=model,
            request=request,
            state=state,
            skill_tools=skill_tools,
            uploaded_files_context=uploaded_files_context,
            recorder=recorder,
            max_rounds=max_rounds,
        )

        attachment = next(
            (item for item in attachments if _is_docx_attachment(item)),
            None,
        )
        if attachment is None:
            raise RuntimeError("事故报告仅支持生成 DOCX 附件。")

        final_report_data_resolved = final_report_data or draft_report_data
        generated_at = utcnow()
        next_summary = _build_summary_from_detail(
            detail,
            status="generated",
            updated_at=generated_at,
        )
        next_snapshot = IncidentReportSessionSnapshot(
            form_answers=detail.snapshot.form_answers,
            report_data=final_report_data_resolved,
            generated_attachment=attachment,
            generated_trace_id=trace_id,
            generated_at=generated_at,
            is_locked=True,
            fallback_used=fallback_used,
            polish_error=polish_error,
        )
        await save_incident_session_summary(next_summary)
        await save_incident_session_snapshot(session_id, next_snapshot)
        await touch_incident_session_index(session_id, generated_at.timestamp())

        recorder.add_event(
            event_type="attachment_generated",
            detail={
                "ok": True,
                "attachment_id": attachment.attachment_id,
                "fallback_used": fallback_used,
            },
        )
        recorder.set_final(done_reason="stop", error=None)
        await recorder.flush()
        return IncidentReportGenerateResponse(
            session=next_summary,
            snapshot=next_snapshot,
            trace_id=trace_id,
        )
    except asyncio.CancelledError:
        await _save_generation_failure(
            detail=detail,
            session_id=session_id,
            trace_id=trace_id,
            recorder=recorder,
            fallback_used=fallback_used,
            polish_error=polish_error,
            failure_message="生成任务已取消。",
            done_reason="cancelled",
        )
        raise
    except Exception as exc:  # noqa: BLE001
        failure_message = summarize_exception(exc)
        await _save_generation_failure(
            detail=detail,
            session_id=session_id,
            trace_id=trace_id,
            recorder=recorder,
            fallback_used=fallback_used,
            polish_error=polish_error,
            failure_message=failure_message,
            done_reason="error",
            exc=exc,
        )
        raise


async def delete_incident_report_session(session_id: str) -> bool:
    deleted_session = await delete_incident_session_records(session_id)
    deleted_attachments = delete_attachments_for_conversation(session_id)
    deleted_traces = await delete_agent_traces_for_conversation(
        conversation_id=session_id
    )
    await clear_conversation_state(session_id)
    return bool(deleted_session or deleted_attachments > 0 or deleted_traces > 0)


def get_incident_report_form_schema() -> IncidentReportFormSchemaResponse:
    config = _build_incident_interaction_config()
    return IncidentReportFormSchemaResponse(
        intro_message=config.intro_message or "",
        steps=config.steps,
    )
