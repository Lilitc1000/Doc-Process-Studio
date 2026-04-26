import asyncio
from datetime import UTC, datetime

import doc_process_studio.incident_report.service.translation as translation_module
import doc_process_studio.incident_report.service.report_data as report_data_module
import doc_process_studio.incident_report.service.reference as reference_module
from doc_process_studio.incident_report.schemas.common import (
    IncidentFormAnswer,
    IncidentFormSnapshot,
)
from doc_process_studio.skill.models.runtime import SkillPlanDecision


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
    snapshot = IncidentFormSnapshot(
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
    snapshot = IncidentFormSnapshot(
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
