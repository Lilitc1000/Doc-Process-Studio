import asyncio
from datetime import UTC, datetime

import doc_process_studio.incident_report.service.session as session_module
import doc_process_studio.incident_report.service.generation as generation_module
import doc_process_studio.incident_report.service.preview as preview_module
import doc_process_studio.incident_report.service.translation as translation_module
import doc_process_studio.incident_report.service.report_data as report_data_module
import doc_process_studio.incident_report.service.reference as reference_module
from doc_process_studio.chat.models.attachment import ChatAttachment
from doc_process_studio.incident_report.models.incident_report import (
    IncidentFormAnswer,
    IncidentGeneratedVersion,
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
)
from doc_process_studio.incident_report.schemas.response import IncidentReportSessionDetail
from doc_process_studio.skill.models.runtime import SkillPlanDecision


class _FakeRecorder:
    def __init__(self, **_kwargs):
        self.events: list[dict] = []
        self.final: dict[str, str | None] = {}

    def add_event(self, *, event_type: str, detail: dict) -> None:
        self.events.append({"event_type": event_type, "detail": detail})

    def set_final(self, *, done_reason: str | None, error: str | None) -> None:
        self.final = {
            "done_reason": done_reason,
            "error": error,
        }

    async def flush(self) -> None:
        return None


def _build_docx_attachment(attachment_id: str, name: str) -> ChatAttachment:
    return ChatAttachment(
        attachment_id=attachment_id,
        name=name,
        source="generated",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=64 * 1024,
        size_label="64 KB",
        download_url=f"/api/attachments/{attachment_id}/download",
        expires_at=datetime.now(UTC),
    )


def _build_detail() -> IncidentReportSessionDetail:
    now = datetime.now(UTC)
    return IncidentReportSessionDetail(
        id="incident-session-1",
        title="事故报告-2026/04/14 12:30",
        status="draft",
        created_at=now,
        updated_at=now,
        snapshot=IncidentReportSessionSnapshot(
            form_answers={
                "quick_narrative": IncidentFormAnswer(
                    value="3月12日下午3点客户说下单报错。", custom_value=""
                ),
            },
            report_data=None,
            generated_attachment=None,
            generated_versions=[],
            generated_trace_id=None,
            section_trace_ids={},
            generated_at=None,
            polish_error=None,
        ),
    )


def test_quick_generate_body_updates_form_answers_and_trace(monkeypatch) -> None:
    detail = _build_detail()
    captured = {
        "saved_summaries": [],
        "saved_snapshots": [],
    }

    async def fake_get_incident_report_session(session_id: str):
        assert session_id == "incident-session-1"
        return detail

    async def fake_save_incident_session_summary(
        summary: IncidentReportSessionSummary,
    ) -> None:
        captured["saved_summaries"].append(summary)

    async def fake_save_incident_session_snapshot(
        session_id: str,
        snapshot: IncidentReportSessionSnapshot,
    ) -> None:
        assert session_id == "incident-session-1"
        captured["saved_snapshots"].append(snapshot)

    async def fake_touch_incident_session_index(session_id: str, score: float) -> None:
        assert session_id == "incident-session-1"
        assert score > 0

    async def fake_detect_generation_language_with_model(**kwargs):
        assert kwargs["section_id"] == "quick"
        return "zh", "mock_detect_zh"

    async def fake_verify_generation_language_with_model(**kwargs):
        assert kwargs["expected_language"] == "zh"
        return True, "zh", "mock_verify_ok"

    async def fake_select_for_workspace_reference(**kwargs):
        available_skills = kwargs["available_skills"]
        available_ids = {item.id for item in available_skills}
        assert "body-sections/quick-mode.md" in available_ids
        assert "body-sections/common.md" in available_ids
        assert kwargs["reference_select_limit"] == 4
        return SkillPlanDecision(
            planner_model="qwen3-coder-next:latest",
            required_skill_ids=["body-sections/common.md"],
            optional_skill_ids=["body-sections/quick-mode.md"],
            missing_explicit_skill_ids=[],
            active_skill_ids=["body-sections/common.md", "body-sections/quick-mode.md"],
            primary_skill_id="body-sections/common.md",
            confidence=0.92,
            reasons={"planner": "planner:统一规划器选择了 common + quick-mode"},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    async def fake_stream_chat_completion(*, model: str, messages, tools):
        assert model == "qwen3-coder-next:latest"
        assert messages
        assert tools == []
        assert "系统级技能提示（document-assistant）" in messages[0]["content"]
        assert "本次输出语言已确定为中文（简体中文）" in messages[0]["content"]
        assert "语言策略：本次输出语言已确定为中文（简体中文）" in messages[-1]["content"]
        assert "参考文档" in messages[-1]["content"]
        yield {
            "message": {
                "role": "assistant",
                "content": (
                    '{"description":"客户反馈下单报错，定位数据库CPU打满。",'
                    '"affected_date_summary":"12/03/2026 15:00 - 12/03/2026 16:00",'
                    '"timeline":[{"time":"12/03/2026 15:00","event":"客户报错","resolution":"服务降级","evidence":"监控告警"}],'
                    '"impact_scope":"下单链路","impact_severity":"High","business_impact":"下单受阻",'
                    '"trigger":"慢查询未命中索引","root_cause":"新版本慢查询未建索引","follow_up_actions":"加强 code review"}'
                ),
            },
            "done": False,
        }
        yield {
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "stop",
        }
        yield None

    monkeypatch.setattr(generation_module, "AgentTraceRecorder", _FakeRecorder)
    monkeypatch.setattr(
        session_module,
        "get_incident_report_session",
        fake_get_incident_report_session,
    )
    monkeypatch.setattr(
        session_module,
        "save_incident_session_summary",
        fake_save_incident_session_summary,
    )
    monkeypatch.setattr(
        session_module,
        "save_incident_session_snapshot",
        fake_save_incident_session_snapshot,
    )
    monkeypatch.setattr(
        session_module,
        "touch_incident_session_index",
        fake_touch_incident_session_index,
    )
    monkeypatch.setattr(
        generation_module,
        "_detect_generation_language_with_model",
        fake_detect_generation_language_with_model,
    )
    monkeypatch.setattr(
        generation_module,
        "_verify_generation_language_with_model",
        fake_verify_generation_language_with_model,
    )
    monkeypatch.setattr(
        generation_module,
        "stream_chat_completion",
        fake_stream_chat_completion,
    )
    monkeypatch.setattr(
        reference_module,
        "select_for_workspace_reference",
        fake_select_for_workspace_reference,
    )
    monkeypatch.setattr(generation_module.settings, "ollama_base_url", "http://ollama.local")

    result = asyncio.run(
        session_module.generate_incident_report_body_from_quick_input(
            session_id="incident-session-1",
            model="qwen3-coder-next:latest",
            reranker_model="nomic-embed-text:latest",
        )
    )

    assert result is not None
    assert result.section_id == "quick"
    assert result.trace_id != ""
    assert result.snapshot.generated_trace_id == result.trace_id
    assert result.snapshot.section_trace_ids.get("quick") == result.trace_id
    assert (
        result.snapshot.form_answers["body_description"].value
        == "客户反馈下单报错，定位数据库CPU打满。"
    )
    assert isinstance(result.snapshot.form_answers["body_timeline"].value, list)


def test_quick_generate_body_respects_english_input_language(monkeypatch) -> None:
    detail = _build_detail()
    detail.snapshot.form_answers["quick_narrative"] = IncidentFormAnswer(
        value="At 3 PM, users reported checkout failures on the order service.",
        custom_value="",
    )

    async def fake_get_incident_report_session(session_id: str):
        assert session_id == "incident-session-1"
        return detail

    async def fake_save_incident_session_summary(
        _summary: IncidentReportSessionSummary,
    ) -> None:
        return None

    async def fake_save_incident_session_snapshot(
        _session_id: str,
        _snapshot: IncidentReportSessionSnapshot,
    ) -> None:
        return None

    async def fake_touch_incident_session_index(_session_id: str, _score: float) -> None:
        return None

    async def fake_detect_generation_language_with_model(**kwargs):
        assert kwargs["section_id"] == "quick"
        return "en", "mock_detect_en"

    async def fake_verify_generation_language_with_model(**kwargs):
        assert kwargs["expected_language"] == "en"
        return True, "en", "mock_verify_ok"

    async def fake_select_for_workspace_reference(**_kwargs):
        return SkillPlanDecision(
            planner_model="qwen3-coder-next:latest",
            required_skill_ids=["body-sections/common.md"],
            optional_skill_ids=["body-sections/quick-mode.md"],
            missing_explicit_skill_ids=[],
            active_skill_ids=["body-sections/common.md", "body-sections/quick-mode.md"],
            primary_skill_id="body-sections/common.md",
            confidence=0.9,
            reasons={},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    async def fake_stream_chat_completion(*, model: str, messages, tools):
        assert model == "qwen3-coder-next:latest"
        assert tools == []
        assert "系统级技能提示（document-assistant）" in messages[0]["content"]
        assert "本次输出语言已确定为英文（English）" in messages[0]["content"]
        assert "语言策略：本次输出语言已确定为英文（English）" in messages[-1]["content"]
        yield {
            "message": {
                "role": "assistant",
                "content": (
                    '{"description":"Users experienced checkout failures on the order service.",'
                    '"affected_date_summary":"12/03/2026 15:00 - 12/03/2026 16:00",'
                    '"timeline":[{"time":"12/03/2026 15:00","event":"Users reported checkout failures","resolution":"Traffic was shifted to a safe version","evidence":"Alert from API error dashboard"}],'
                    '"impact_scope":"Checkout flow","impact_severity":"High","business_impact":"Order conversion dropped during peak hours",'
                    '"trigger":"A slow query path was introduced in the new release","root_cause":"Missing index on a hot table after deployment","follow_up_actions":"Add release SQL checklist"}'
                ),
            },
            "done": False,
        }
        yield {
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "stop",
        }
        yield None

    monkeypatch.setattr(generation_module, "AgentTraceRecorder", _FakeRecorder)
    monkeypatch.setattr(
        session_module,
        "get_incident_report_session",
        fake_get_incident_report_session,
    )
    monkeypatch.setattr(
        session_module,
        "save_incident_session_summary",
        fake_save_incident_session_summary,
    )
    monkeypatch.setattr(
        session_module,
        "save_incident_session_snapshot",
        fake_save_incident_session_snapshot,
    )
    monkeypatch.setattr(
        session_module,
        "touch_incident_session_index",
        fake_touch_incident_session_index,
    )
    monkeypatch.setattr(
        generation_module,
        "_detect_generation_language_with_model",
        fake_detect_generation_language_with_model,
    )
    monkeypatch.setattr(
        generation_module,
        "_verify_generation_language_with_model",
        fake_verify_generation_language_with_model,
    )
    monkeypatch.setattr(
        generation_module,
        "stream_chat_completion",
        fake_stream_chat_completion,
    )
    monkeypatch.setattr(
        reference_module,
        "select_for_workspace_reference",
        fake_select_for_workspace_reference,
    )
    monkeypatch.setattr(generation_module.settings, "ollama_base_url", "http://ollama.local")

    result = asyncio.run(
        session_module.generate_incident_report_body_from_quick_input(
            session_id="incident-session-1",
            model="qwen3-coder-next:latest",
        )
    )

    assert result is not None
    assert (
        result.snapshot.form_answers["body_description"].value
        == "Users experienced checkout failures on the order service."
    )


def test_reference_selector_chooses_section_reference(monkeypatch) -> None:
    async def fake_select_for_workspace_reference(**kwargs):
        planner_messages = kwargs["messages"]
        assert planner_messages
        first_content = (
            planner_messages[0].content
            if hasattr(planner_messages[0], "content")
            else planner_messages[0]["content"]
        )
        assert "incident-report SKILL.md" in first_content
        return SkillPlanDecision(
            planner_model="qwen3-coder-next:latest",
            required_skill_ids=["body-sections/common.md"],
            optional_skill_ids=["body-sections/impact.md"],
            missing_explicit_skill_ids=[],
            active_skill_ids=["body-sections/common.md", "body-sections/impact.md"],
            primary_skill_id="body-sections/common.md",
            confidence=0.88,
            reasons={"planner": "planner:统一规划器选择了 impact 参考"},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        reference_module,
        "select_for_workspace_reference",
        fake_select_for_workspace_reference,
    )

    reference_context, selected_files, selection_reason = asyncio.run(
        reference_module.resolve_generation_reference_context(
            model="qwen3-coder-next:latest",
            section_id="impact",
            timeline_index=None,
            prompt="仅生成影响范围与严重级别",
            context_json='{"impact_scope":"下单链路"}',
        )
    )

    assert "body-sections/impact.md" in selected_files
    assert "impact.md" in reference_context
    assert selection_reason.startswith("planner:")


def test_quick_generate_retries_when_language_verification_mismatch(monkeypatch) -> None:
    detail = _build_detail()
    detail.snapshot.form_answers["quick_narrative"] = IncidentFormAnswer(
        value="Checkout fails after deployment.",
        custom_value="",
    )

    async def fake_get_incident_report_session(session_id: str):
        assert session_id == "incident-session-1"
        return detail

    async def fake_save_incident_session_summary(_summary: IncidentReportSessionSummary) -> None:
        return None

    async def fake_save_incident_session_snapshot(
        _session_id: str,
        _snapshot: IncidentReportSessionSnapshot,
    ) -> None:
        return None

    async def fake_touch_incident_session_index(_session_id: str, _score: float) -> None:
        return None

    async def fake_select_for_workspace_reference(**_kwargs):
        return SkillPlanDecision(
            planner_model="qwen3-coder-next:latest",
            required_skill_ids=["body-sections/common.md"],
            optional_skill_ids=["body-sections/quick-mode.md"],
            missing_explicit_skill_ids=[],
            active_skill_ids=["body-sections/common.md", "body-sections/quick-mode.md"],
            primary_skill_id="body-sections/common.md",
            confidence=0.9,
            reasons={},
            candidates=[],
            created_at=datetime.now(UTC),
        )

    async def fake_detect_generation_language_with_model(**_kwargs):
        return "en", "mock_detect_en"

    verify_counter = {"value": 0}

    async def fake_verify_generation_language_with_model(**_kwargs):
        verify_counter["value"] += 1
        if verify_counter["value"] == 1:
            return False, "zh", "mock_mismatch"
        return True, "en", "mock_match"

    stream_counter = {"value": 0}

    async def fake_stream_chat_completion(*, model: str, messages, tools):
        assert model == "qwen3-coder-next:latest"
        assert tools == []
        stream_counter["value"] += 1
        if stream_counter["value"] == 2:
            assert "上一次输出语言不符合要求" in messages[0]["content"]
        if stream_counter["value"] == 1:
            payload = (
                '{"description":"故障描述",'
                '"affected_date_summary":"12/03/2026 15:00 - 12/03/2026 16:00",'
                '"timeline":[{"time":"12/03/2026 15:00","event":"事件","resolution":"恢复","evidence":"告警"}],'
                '"impact_scope":"范围","impact_severity":"High","business_impact":"影响",'
                '"trigger":"触发","root_cause":"根因","follow_up_actions":"动作"}'
            )
        else:
            payload = (
                '{"description":"English description",'
                '"affected_date_summary":"12/03/2026 15:00 - 12/03/2026 16:00",'
                '"timeline":[{"time":"12/03/2026 15:00","event":"Incident","resolution":"Recovered","evidence":"Alert"}],'
                '"impact_scope":"Checkout","impact_severity":"High","business_impact":"Conversion impacted",'
                '"trigger":"Deployment issue","root_cause":"Missing index","follow_up_actions":"Add checks"}'
            )
        yield {
            "message": {
                "role": "assistant",
                "content": payload,
            },
            "done": False,
        }
        yield {
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "stop",
        }
        yield None

    monkeypatch.setattr(generation_module, "AgentTraceRecorder", _FakeRecorder)
    monkeypatch.setattr(
        session_module,
        "get_incident_report_session",
        fake_get_incident_report_session,
    )
    monkeypatch.setattr(
        session_module,
        "save_incident_session_summary",
        fake_save_incident_session_summary,
    )
    monkeypatch.setattr(
        session_module,
        "save_incident_session_snapshot",
        fake_save_incident_session_snapshot,
    )
    monkeypatch.setattr(
        session_module,
        "touch_incident_session_index",
        fake_touch_incident_session_index,
    )
    monkeypatch.setattr(
        generation_module,
        "_detect_generation_language_with_model",
        fake_detect_generation_language_with_model,
    )
    monkeypatch.setattr(
        generation_module,
        "_verify_generation_language_with_model",
        fake_verify_generation_language_with_model,
    )
    monkeypatch.setattr(
        generation_module,
        "stream_chat_completion",
        fake_stream_chat_completion,
    )
    monkeypatch.setattr(
        reference_module,
        "select_for_workspace_reference",
        fake_select_for_workspace_reference,
    )
    monkeypatch.setattr(generation_module.settings, "ollama_base_url", "http://ollama.local")

    result = asyncio.run(
        session_module.generate_incident_report_body_from_quick_input(
            session_id="incident-session-1",
            model="qwen3-coder-next:latest",
        )
    )

    assert result is not None
    assert stream_counter["value"] == 2
    assert verify_counter["value"] == 2
    assert result.snapshot.form_answers["body_description"].value == "English description"


def test_preview_incident_report_attachment_uses_version_attachment(monkeypatch) -> None:
    detail = _build_detail()
    detail.snapshot.generated_versions = [
        IncidentGeneratedVersion(
            version=1,
            label="V1 2026-04-14 12:40:00",
            generated_at=datetime.now(UTC),
            attachment=_build_docx_attachment(
                "generated-attachment-1",
                "incident-report-v1.docx",
            ),
            report_data={},
        )
    ]

    async def fake_get_incident_report_session(session_id: str):
        assert session_id == "incident-session-1"
        return detail

    def fake_load_docx_bytes_from_attachment(attachment_id: str):
        assert attachment_id == "generated-attachment-1"
        return b"fake-docx-bytes"

    def fake_build_preview_payload_from_docx_bytes(docx_bytes: bytes):
        assert docx_bytes == b"fake-docx-bytes"
        return "<p>preview-html</p>", "cGRmLWJhc2U2NA==", ["warn-1"]

    monkeypatch.setattr(
        session_module,
        "get_incident_report_session",
        fake_get_incident_report_session,
    )
    monkeypatch.setattr(
        session_module,
        "load_docx_bytes_from_attachment",
        fake_load_docx_bytes_from_attachment,
    )
    monkeypatch.setattr(
        session_module,
        "build_preview_payload_from_docx_bytes",
        fake_build_preview_payload_from_docx_bytes,
    )

    result = asyncio.run(
        session_module.preview_incident_report_attachment(
            session_id="incident-session-1",
            version=1,
        )
    )

    assert result is not None
    assert result.source == "version"
    assert result.version == 1
    assert result.html == "<p>preview-html</p>"
    assert result.pdf_base64 == "cGRmLWJhc2U2NA=="
    assert result.warnings == ["warn-1"]


def test_preview_incident_report_attachment_draft_hits_cache(monkeypatch) -> None:
    detail = _build_detail()
    translate_calls = {"count": 0}
    render_calls = {"count": 0}
    preview_calls = {"count": 0}

    async def fake_get_incident_report_session(session_id: str):
        assert session_id == "incident-session-1"
        return detail

    def fake_build_report_data_from_snapshot(*_args, **_kwargs):
        return {
            "reference_no": "DAS-20260417-001",
            "body": {"description": "中文描述"},
        }, []

    async def fake_translate_report_data_to_english(*, report_data: dict):
        translate_calls["count"] += 1
        return report_data

    def fake_render_docx_bytes_from_report_data(report_data: dict):
        render_calls["count"] += 1
        assert report_data["reference_no"] == "DAS-20260417-001"
        return b"fake-draft-docx"

    def fake_build_preview_payload_from_docx_bytes(docx_bytes: bytes):
        preview_calls["count"] += 1
        assert docx_bytes == b"fake-draft-docx"
        return "<p>draft-preview</p>", "cGRmLWJhc2U2NA==", []

    monkeypatch.setattr(
        session_module,
        "get_incident_report_session",
        fake_get_incident_report_session,
    )
    monkeypatch.setattr(
        session_module,
        "build_report_data_from_snapshot",
        fake_build_report_data_from_snapshot,
    )
    monkeypatch.setattr(
        session_module,
        "translate_report_data_to_english",
        fake_translate_report_data_to_english,
    )
    monkeypatch.setattr(
        session_module,
        "render_docx_bytes_from_report_data",
        fake_render_docx_bytes_from_report_data,
    )
    monkeypatch.setattr(
        session_module,
        "build_preview_payload_from_docx_bytes",
        fake_build_preview_payload_from_docx_bytes,
    )

    preview_module._PREVIEW_RESULT_CACHE.clear()
    translation_module._TRANSLATION_CACHE.clear()

    first = asyncio.run(
        session_module.preview_incident_report_attachment(
            session_id="incident-session-1",
            model="qwen3-coder-next:latest",
        )
    )
    second = asyncio.run(
        session_module.preview_incident_report_attachment(
            session_id="incident-session-1",
            model="qwen3-coder-next:latest",
        )
    )

    assert first is not None
    assert second is not None
    assert first.html == "<p>draft-preview</p>"
    assert second.html == "<p>draft-preview</p>"
    assert translate_calls["count"] == 1
    assert render_calls["count"] == 1
    assert preview_calls["count"] == 1


def test_translate_report_data_to_english_uses_python_library_and_cache(
    monkeypatch,
) -> None:
    call_counter = {"batch": 0, "single": 0}

    class _FakeTranslator:
        def __init__(self, **_kwargs):
            return

        def translate_batch(self, texts: list[str]) -> list[str]:
            call_counter["batch"] += 1
            translated: list[str] = []
            for text in texts:
                if text == "客户反馈下单报错":
                    translated.append("Customer reported order placement errors")
                else:
                    translated.append(text)
            return translated

        def translate(self, text: str) -> str:
            call_counter["single"] += 1
            if text == "客户反馈下单报错":
                return "Customer reported order placement errors"
            return text

    monkeypatch.setattr(translation_module, "GoogleTranslator", _FakeTranslator)
    translation_module._TRANSLATION_CACHE.clear()

    report_data = {
        "reference_no": "DAS-20260420-001",
        "report_body": {
            "description": "客户反馈下单报错",
        },
    }

    translated_once = asyncio.run(
        translation_module.translate_report_data_to_english(
            report_data=report_data,
        )
    )
    translated_twice = asyncio.run(
        translation_module.translate_report_data_to_english(
            report_data=report_data,
        )
    )

    assert translated_once["reference_no"] == "DAS-20260420-001"
    assert (
        translated_once["report_body"]["description"]
        == "Customer reported order placement errors"
    )
    assert (
        translated_twice["report_body"]["description"]
        == "Customer reported order placement errors"
    )
    assert call_counter["batch"] == 1
    assert call_counter["single"] == 0


def test_build_report_data_supports_rich_text_appendix() -> None:
    snapshot = IncidentReportSessionSnapshot(
        form_answers={
            "appendix_notes": IncidentFormAnswer(
                value=(
                    "<p>附录说明第一行</p><p>附录说明第二行</p>"
                    "<p><img alt='chart.png' src='data:image/png;base64,AAAA' /></p>"
                ),
                custom_value="",
            ),
        }
    )
    report_data, missing = report_data_module.build_report_data_from_snapshot(
        snapshot,
        strict_required=False,
    )

    assert report_data is not None
    assert isinstance(missing, list)
    assert report_data["appendix"]["notes"] == "附录说明第一行\n附录说明第二行"
    assert report_data["appendix"]["images"] == [
        {
            "name": "chart.png",
            "data_url": "data:image/png;base64,AAAA",
        }
    ]


def test_build_report_data_rich_text_appendix_image_only_does_not_fallback_raw_html() -> None:
    snapshot = IncidentReportSessionSnapshot(
        form_answers={
            "appendix_notes": IncidentFormAnswer(
                value="<p><img alt='photo.png' src='data:image/png;base64,BBBB' /></p>",
                custom_value="",
            ),
        }
    )
    report_data, missing = report_data_module.build_report_data_from_snapshot(
        snapshot,
        strict_required=False,
    )

    assert report_data is not None
    assert isinstance(missing, list)
    assert report_data["appendix"]["notes"] == ""
    assert report_data["appendix"]["images"] == [
        {
            "name": "photo.png",
            "data_url": "data:image/png;base64,BBBB",
        }
    ]


def test_create_incident_report_session_initializes_v1_version(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_save_incident_session_summary(
        summary: IncidentReportSessionSummary,
    ) -> None:
        captured["summary"] = summary

    async def fake_save_incident_session_snapshot(
        session_id: str,
        snapshot: IncidentReportSessionSnapshot,
    ) -> None:
        captured["session_id"] = session_id
        captured["snapshot"] = snapshot

    async def fake_touch_incident_session_index(session_id: str, score: float) -> None:
        captured["touch"] = (session_id, score)

    def fake_build_report_data_from_snapshot(*_args, **_kwargs):
        return {"reference_no": "DAS-20260417-001"}, []

    def fake_render_docx_bytes_from_report_data(report_data: dict):
        assert report_data["reference_no"] == "DAS-20260417-001"
        return b"fake-docx-bytes"

    def fake_save_docx_bytes_as_generated_attachment(**kwargs):
        assert kwargs["docx_bytes"] == b"fake-docx-bytes"
        return _build_docx_attachment("generated-attachment-v1", "incident-report-v1.docx")

    monkeypatch.setattr(
        session_module,
        "save_incident_session_summary",
        fake_save_incident_session_summary,
    )
    monkeypatch.setattr(
        session_module,
        "save_incident_session_snapshot",
        fake_save_incident_session_snapshot,
    )
    monkeypatch.setattr(
        session_module,
        "touch_incident_session_index",
        fake_touch_incident_session_index,
    )
    monkeypatch.setattr(
        session_module,
        "build_report_data_from_snapshot",
        fake_build_report_data_from_snapshot,
    )
    monkeypatch.setattr(
        session_module,
        "render_docx_bytes_from_report_data",
        fake_render_docx_bytes_from_report_data,
    )
    monkeypatch.setattr(
        session_module,
        "save_docx_bytes_as_generated_attachment",
        fake_save_docx_bytes_as_generated_attachment,
    )

    result = asyncio.run(
        session_module.create_incident_report_session(title="事故报告-测试"),
    )

    assert result.id != ""
    snapshot = captured.get("snapshot")
    assert isinstance(snapshot, IncidentReportSessionSnapshot)
    assert len(snapshot.generated_versions) == 1
    assert snapshot.generated_versions[0].version == 1
    assert snapshot.generated_attachment is not None
    assert snapshot.generated_attachment.attachment_id == "generated-attachment-v1"
