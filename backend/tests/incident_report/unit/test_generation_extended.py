import asyncio
from datetime import UTC, datetime

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
            reasons={"planner": "planner:unified planner selected impact reference"},
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
            prompt="Generate impact scope and severity",
            context_json='{"impact_scope":"Order placement chain"}',
        )
    )

    assert "body-sections/impact.md" in selected_files
    assert "impact.md" in reference_context
    assert selection_reason.startswith("planner:")


def test_translate_report_data_returns_input_unchanged() -> None:
    import doc_process_studio.incident_report.service.translation as translation_module

    report_data = {
        "reference_no": "DAS-20260420-001",
        "report_body": {
            "description": "Customer reported order placement errors",
        },
    }

    result = asyncio.run(
        translation_module.translate_report_data_to_english(
            report_data=report_data,
        )
    )

    assert result == report_data
    assert result["reference_no"] == "DAS-20260420-001"
    assert result["report_body"]["description"] == "Customer reported order placement errors"


def test_build_report_data_supports_rich_text_appendix() -> None:
    snapshot = IncidentFormSnapshot(
        form_answers={
            "appendix_notes": IncidentFormAnswer(
                value=(
                    "<p>Appendix note line 1</p><p>Appendix note line 2</p>"
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
    assert report_data["appendix"]["notes"] == "Appendix note line 1\nAppendix note line 2"
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
