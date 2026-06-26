"""报告正文生成应用服务。

编排快填生成和分段生成的用例：加载报告 → 权限检查 → 构建请求 →
调用 LLM → 解析结果 → 回填字段 → 持久化 → 返回。
所有跨域调用通过端口抽象，不直接依赖 service 层和外部域。
"""

import logging
from copy import deepcopy
from typing import Any
from uuid import uuid4

import httpx

from ....common.infrastructure.config import settings
from ....common.utils.error_utils import summarize_exception
from ....common.utils.text_utils import parse_json_object
from ...domain.values.errors import PermissionDeniedError, ReportNotFoundError
from ...domain.values.permission import Permission
from ..dtos import IncidentBodyGenerateResponse, IncidentFormSnapshot
from ..ports import (
    DocumentAssistantPort,
    LLMStreamingPort,
    PermissionChecker,
    ReferenceContextPort,
    ReportRepository,
    TraceRecorderPort,
)

logger = logging.getLogger(__name__)


class GenerationService:
    """报告正文生成用例：快速生成 + 分段生成。"""

    def __init__(
        self,
        repo: ReportRepository,
        checker: PermissionChecker,
        llm: LLMStreamingPort,
        trace: TraceRecorderPort,
        reference: ReferenceContextPort,
        doc_assistant: DocumentAssistantPort,
    ) -> None:
        self._repo = repo
        self._checker = checker
        self._llm = llm
        self._trace = trace
        self._reference = reference
        self._doc_assistant = doc_assistant

    async def quick_generate(
        self,
        *,
        report_id: str,
        user_id: str,
        model: str | None = None,
        reranker_model: str | None = None,
    ) -> IncidentBodyGenerateResponse:
        report = await self._repo.get(report_id)
        if report is None:
            raise ReportNotFoundError(report_id)
        await self._check_edit_permission(user_id, report.reporter_id, report.assignee_id)

        from ...infrastructure.utils.generation import _build_quick_generation_request, _build_snapshot_from_form_data

        snapshot = _build_snapshot_from_form_data(report.form_data)
        effective_model = model or "gemma4:e4b"
        prompt, context_json = _build_quick_generation_request(snapshot)

        from ...infrastructure.utils.generation import _apply_quick_generation_payload

        return await self._run_body_generation_with_trace(
            report_id=report_id,
            snapshot=snapshot,
            model=effective_model,
            reranker_model=reranker_model,
            section_id="quick",
            timeline_index=None,
            prompt=prompt,
            context_json=context_json,
            apply_payload=lambda fa, p: _apply_quick_generation_payload(form_answers=fa, payload=p),
        )

    async def generate_section(
        self,
        *,
        report_id: str,
        section_id: str,
        timeline_index: int | None = None,
        user_id: str,
        model: str | None = None,
        reranker_model: str | None = None,
    ) -> IncidentBodyGenerateResponse:
        report = await self._repo.get(report_id)
        if report is None:
            raise ReportNotFoundError(report_id)
        await self._check_edit_permission(user_id, report.reporter_id, report.assignee_id)

        from ...infrastructure.utils.generation import _build_section_generation_prompt, _build_snapshot_from_form_data

        snapshot = _build_snapshot_from_form_data(report.form_data)
        effective_model = model or "gemma4:e4b"
        prompt, context_json = _build_section_generation_prompt(
            snapshot,
            section_id=section_id,
            timeline_index=timeline_index,
        )

        from ...infrastructure.utils.generation import _apply_section_payload

        return await self._run_body_generation_with_trace(
            report_id=report_id,
            snapshot=snapshot,
            model=effective_model,
            reranker_model=reranker_model,
            section_id=section_id,
            timeline_index=timeline_index,
            prompt=prompt,
            context_json=context_json,
            apply_payload=lambda fa, p: _apply_section_payload(
                form_answers=fa,
                section_id=section_id,
                timeline_index=timeline_index,
                payload=p,
            ),
        )

    # ---- 权限检查 ----
    async def _check_edit_permission(self, user_id: str, reporter_id: str, assignee_id: str | None) -> None:
        """检查用户是否有编辑权限。"""
        perms = await self._checker.permissions_of(user_id)
        can_edit = (
            (reporter_id == user_id and Permission.REPORT_EDIT_OWN in perms)
            or (assignee_id == user_id and Permission.REPORT_EDIT_ASSIGNED in perms)
            or Permission.REPORT_EDIT_ALL in perms
        )
        if not can_edit:
            raise PermissionDeniedError("无权对此报告进行生成操作")

    # ---- 核心生成流程 ----
    async def _run_body_generation_with_trace(
        self,
        *,
        report_id: str,
        snapshot: IncidentFormSnapshot,
        model: str,
        reranker_model: str | None,
        section_id: str,
        timeline_index: int | None,
        prompt: str,
        context_json: str,
        apply_payload: Any,
    ) -> IncidentBodyGenerateResponse:
        if not settings.ollama_base_url:
            raise RuntimeError("OLLAMA_BASE_URL is not configured.")

        effective_reranker_model = (reranker_model or "").strip() or model
        trace_id = uuid4().hex
        recorder = self._trace.create_recorder(
            trace_id=trace_id,
            tenant_id="default",
            conversation_id=report_id,
            user_message_id=f"incident-body-{section_id}",
            model=model,
            reranker_model=effective_reranker_model,
        )
        await self._trace.add_event(
            recorder,
            "body_generation_request",
            {
                "section_id": section_id,
                "timeline_index": timeline_index,
                "language_policy": "english_fixed",
            },
        )
        await self._trace.flush_recorder(recorder)

        # 参考文档选择
        reference_context = "[fallback]\nReference documentation unavailable, generate from context."
        selected_reference_files: list[str] = []
        reference_selection_reason = "fallback:init"

        try:
            (
                reference_context,
                selected_reference_files,
                reference_selection_reason,
            ) = await self._reference.resolve(
                model=model,
                section_id=section_id,
                timeline_index=timeline_index,
                prompt=prompt,
                context_json=context_json,
            )
            await self._trace.add_event(
                recorder,
                "body_generation_reference_selection",
                {
                    "section_id": section_id,
                    "selected_reference_files": selected_reference_files,
                    "selection_reason": reference_selection_reason,
                },
            )
            await self._trace.flush_recorder(recorder)

            # 调用 LLM
            from ...infrastructure.utils.generation import _build_body_generation_messages

            messages = _build_body_generation_messages(
                prompt=prompt,
                context_json=context_json,
                reference_context=reference_context,
                document_assistant_prompt=self._doc_assistant.get_default_prompt(),
            )
            response_text, done_reason = await self._llm.stream_chat(model=model, messages=messages)

        except httpx.HTTPError as exc:
            await self._trace.add_event(
                recorder,
                "body_generation_error",
                {
                    "ok": False,
                    "error": summarize_exception(exc),
                },
            )
            await self._trace.set_final(recorder, done_reason="error", error=summarize_exception(exc))
            await self._trace.flush_recorder(recorder)
            raise RuntimeError(f"Body generation failed: {summarize_exception(exc)}") from exc

        # 解析 JSON
        payload = parse_json_object(response_text)
        if payload is None:
            await self._trace.add_event(
                recorder,
                "body_generation_error",
                {
                    "ok": False,
                    "error": "Model did not return valid JSON.",
                    "raw_preview": response_text[:500],
                },
            )
            await self._trace.set_final(recorder, done_reason="error", error="Model did not return valid JSON.")
            await self._trace.flush_recorder(recorder)
            raise RuntimeError("Model did not return valid JSON.")

        # 应用生成结果
        form_answers = deepcopy(snapshot.form_answers)
        apply_payload(form_answers, payload)

        # 构建新 snapshot

        next_snapshot = snapshot.model_copy(deep=True)
        next_snapshot.form_answers = form_answers
        next_snapshot.generated_trace_id = trace_id
        section_trace_ids = dict(next_snapshot.section_trace_ids)
        section_key = section_id
        if section_id == "timeline_item" and timeline_index is not None:
            section_key = f"timeline_item_{timeline_index}"
        section_trace_ids[section_key] = trace_id
        next_snapshot.section_trace_ids = section_trace_ids
        next_snapshot.polish_error = None

        # 持久化
        form_data_for_db = {key: ans.model_dump() for key, ans in next_snapshot.form_answers.items()}
        await self._repo.update_form_data(
            report_id,
            form_data=form_data_for_db,
            report_data=next_snapshot.report_data,
        )

        # 记录追踪
        await self._trace.add_event(
            recorder,
            "body_generation_result",
            {
                "ok": True,
                "section_id": section_id,
            },
        )
        await self._trace.set_final(recorder, done_reason=done_reason, error=None)
        await self._trace.flush_recorder(recorder)

        return IncidentBodyGenerateResponse(
            report_id=report_id,
            form_answers=form_answers,
            trace_id=trace_id,
            section_id=section_id,
            timeline_index=timeline_index,
        )
