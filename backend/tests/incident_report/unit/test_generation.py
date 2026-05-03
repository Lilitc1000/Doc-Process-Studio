import json

import doc_process_studio.incident_report.service.generation as generation_module
from doc_process_studio.incident_report.schemas.common import IncidentFormAnswer, IncidentFormSnapshot


def _make_snapshot(**overrides) -> IncidentFormSnapshot:
    defaults = dict(form_answers={}, report_data=None)
    defaults.update(overrides)
    return IncidentFormSnapshot(**defaults)


def test_build_default_title():
    from datetime import UTC, datetime
    now = datetime(2026, 4, 8, 9, 10, tzinfo=UTC)
    title = generation_module._build_default_title(now)
    assert "2026/04/08" in title
    assert "09:10" in title
    assert "Incident-Report" in title


def test_build_quick_generation_context():
    snapshot = _make_snapshot(
        form_answers={
            "quick_narrative": IncidentFormAnswer(value="Brief description"),
            "body_description": IncidentFormAnswer(value="Existing description"),
        }
    )
    context = generation_module._build_quick_generation_context(snapshot)
    assert "quick_inputs" in context
    assert "manual_cover_context" in context
    assert "existing_full_body" in context


def test_build_quick_generation_request():
    snapshot = _make_snapshot(
        form_answers={
            "quick_narrative": IncidentFormAnswer(value="Brief description"),
        }
    )
    prompt, context_json = generation_module._build_quick_generation_request(snapshot)
    assert "quick-fill" in prompt
    assert "JSON" in prompt
    parsed = json.loads(context_json)
    assert "quick_inputs" in parsed


def test_build_section_generation_prompt_description():
    snapshot = _make_snapshot(form_answers={})
    prompt, context = generation_module._build_section_generation_prompt(
        snapshot, section_id="description", timeline_index=None,
    )
    assert "body_description" in prompt


def test_build_section_generation_prompt_timeline():
    snapshot = _make_snapshot(form_answers={})
    prompt, context = generation_module._build_section_generation_prompt(
        snapshot, section_id="timeline", timeline_index=None,
    )
    assert "body_timeline" in prompt


def test_build_section_generation_prompt_impact():
    snapshot = _make_snapshot(form_answers={})
    prompt, context = generation_module._build_section_generation_prompt(
        snapshot, section_id="impact", timeline_index=None,
    )
    assert "impact_scope" in prompt


def test_build_section_generation_prompt_root_cause():
    snapshot = _make_snapshot(form_answers={})
    prompt, context = generation_module._build_section_generation_prompt(
        snapshot, section_id="root_cause", timeline_index=None,
    )
    assert "root_cause" in prompt


def test_build_section_generation_prompt_follow_up():
    snapshot = _make_snapshot(form_answers={})
    prompt, context = generation_module._build_section_generation_prompt(
        snapshot, section_id="follow_up", timeline_index=None,
    )
    assert "follow_up" in prompt


def test_build_section_generation_prompt_timeline_item_invalid_index():
    snapshot = _make_snapshot(form_answers={})
    try:
        generation_module._build_section_generation_prompt(
            snapshot, section_id="timeline_item", timeline_index=0,
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_build_section_generation_prompt_unsupported():
    snapshot = _make_snapshot(form_answers={})
    try:
        generation_module._build_section_generation_prompt(
            snapshot, section_id="unknown", timeline_index=None,
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_build_body_generation_messages():
    messages = generation_module._build_body_generation_messages(
        prompt="Generate description",
        context_json='{"key":"value"}',
        reference_context="Reference documentation content",
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Reference documentation" in messages[1]["content"]
    assert "English" in messages[0]["content"]


def test_apply_quick_generation_payload():
    form_answers = {}
    payload = {
        "description": "AI-generated description",
        "affected_date_summary": "08/04/2026 09:10 - 10:30",
        "timeline": [{"time": "09:10", "event": "Fault occurred"}],
        "impact_scope": "Impact scope",
        "impact_severity": "Major",
        "business_impact": "Business impact",
        "trigger": "Trigger cause",
        "root_cause": "Root cause analysis",
        "follow_up_actions": "Follow-up actions",
    }
    generation_module._apply_quick_generation_payload(
        form_answers=form_answers,
        payload=payload,
    )
    assert form_answers["body_description"].value == "AI-generated description"
    assert form_answers["body_impact_scope"].value == "Impact scope"


def test_apply_section_payload_description():
    form_answers = {}
    generation_module._apply_section_payload(
        form_answers=form_answers,
        section_id="description",
        timeline_index=None,
        payload={"body_description": "New description"},
    )
    assert form_answers["body_description"].value == "New description"


def test_apply_section_payload_timeline():
    form_answers = {}
    generation_module._apply_section_payload(
        form_answers=form_answers,
        section_id="timeline",
        timeline_index=None,
        payload={
            "body_timeline": [{"time": "09:10", "event": "Fault"}],
            "body_affected_date_summary": "Date summary",
        },
    )
    assert "body_timeline" in form_answers


def test_apply_section_payload_impact():
    form_answers = {}
    generation_module._apply_section_payload(
        form_answers=form_answers,
        section_id="impact",
        timeline_index=None,
        payload={
            "body_impact_scope": "Impact scope",
            "body_impact_severity": "Major",
            "body_business_impact": "Business impact",
        },
    )
    assert form_answers["body_impact_scope"].value == "Impact scope"


def test_apply_section_payload_root_cause():
    form_answers = {}
    generation_module._apply_section_payload(
        form_answers=form_answers,
        section_id="root_cause",
        timeline_index=None,
        payload={
            "body_trigger": "Trigger cause",
            "body_root_cause": "Root cause analysis",
        },
    )
    assert form_answers["body_trigger"].value == "Trigger cause"


def test_apply_section_payload_follow_up():
    form_answers = {}
    generation_module._apply_section_payload(
        form_answers=form_answers,
        section_id="follow_up",
        timeline_index=None,
        payload={"body_follow_up": "Follow-up actions"},
    )
    assert form_answers["body_follow_up"].value == "Follow-up actions"


def test_apply_section_payload_unsupported():
    form_answers = {}
    try:
        generation_module._apply_section_payload(
            form_answers=form_answers,
            section_id="unknown",
            timeline_index=None,
            payload={},
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_resolve_document_assistant_prompt_fallback(monkeypatch):
    import doc_process_studio.skill.service.registry as registry_module

    def _fake_get_skill_interface(skill_id):
        raise ValueError("not found")

    monkeypatch.setattr(
        registry_module,
        "get_skill_interface",
        _fake_get_skill_interface,
    )
    result = generation_module._resolve_document_assistant_prompt()
    assert result == ""
