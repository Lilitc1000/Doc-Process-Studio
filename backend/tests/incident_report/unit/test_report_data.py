
from doc_process_studio.incident_report.service.report_data import (
    answer_text,
    answer_value,
    answer_value_from_answers,
    build_report_data_from_snapshot,
    set_answer,
    set_answer_if_non_empty,
)
from doc_process_studio.incident_report.schemas.common import IncidentFormAnswer, IncidentFormSnapshot


def _make_snapshot(**overrides) -> IncidentFormSnapshot:
    defaults = dict(
        form_answers={},
        report_data=None,
    )
    defaults.update(overrides)
    return IncidentFormSnapshot(**defaults)


def test_answer_value_returns_value():
    snapshot = _make_snapshot(form_answers={"key": IncidentFormAnswer(value="hello")})
    assert answer_value(snapshot, "key") == "hello"


def test_answer_value_missing():
    snapshot = _make_snapshot(form_answers={})
    assert answer_value(snapshot, "key") is None


def test_answer_text_returns_stripped():
    snapshot = _make_snapshot(form_answers={"key": IncidentFormAnswer(value="  hello  ")})
    assert answer_text(snapshot, "key") == "hello"


def test_answer_text_none_value():
    snapshot = _make_snapshot(form_answers={"key": IncidentFormAnswer(value=None)})
    assert answer_text(snapshot, "key") == ""


def test_answer_value_from_answers():
    form_answers = {"key": IncidentFormAnswer(value="val")}
    assert answer_value_from_answers(form_answers, "key") == "val"


def test_answer_value_from_answers_missing():
    form_answers = {}
    assert answer_value_from_answers(form_answers, "key") is None


def test_set_answer():
    form_answers = {}
    set_answer(form_answers, "key", "value")
    assert form_answers["key"].value == "value"


def test_set_answer_overwrites():
    form_answers = {"key": IncidentFormAnswer(value="old")}
    set_answer(form_answers, "key", "new")
    assert form_answers["key"].value == "new"


def test_set_answer_if_non_empty():
    form_answers = {}
    set_answer_if_non_empty(form_answers, "key", "value")
    assert form_answers["key"].value == "value"


def test_set_answer_if_non_empty_skips_empty():
    form_answers = {}
    set_answer_if_non_empty(form_answers, "key", "")
    assert "key" not in form_answers


def test_set_answer_if_non_empty_skips_whitespace():
    form_answers = {}
    set_answer_if_non_empty(form_answers, "key", "   ")
    assert "key" not in form_answers


def test_build_report_data_strict_required():
    snapshot = _make_snapshot(form_answers={})
    result, missing = build_report_data_from_snapshot(snapshot, strict_required=True)
    assert result is None
    assert len(missing) > 0


def test_build_report_data_non_strict():
    snapshot = _make_snapshot(form_answers={})
    result, missing = build_report_data_from_snapshot(snapshot, strict_required=False)
    assert result is not None
    assert isinstance(missing, list)


def test_build_report_data_with_minimal_fields():
    snapshot = _make_snapshot(
        form_answers={
            "manual_fault_date": IncidentFormAnswer(value="2026-04-08"),
            "manual_fault_time": IncidentFormAnswer(value="09:10"),
            "manual_reporting_person": IncidentFormAnswer(value="张三"),
            "manual_site_id": IncidentFormAnswer(value="SITE-01"),
            "manual_system": IncidentFormAnswer(value="数据库"),
            "manual_location": IncidentFormAnswer(value="机房A"),
            "manual_fault_symptom": IncidentFormAnswer(value="服务中断"),
            "manual_severity": IncidentFormAnswer(value="P2"),
            "body_description": IncidentFormAnswer(value="事故描述"),
            "body_impact_scope": IncidentFormAnswer(value="影响范围"),
            "body_impact_severity": IncidentFormAnswer(value="Major"),
            "body_root_cause": IncidentFormAnswer(value="根因分析"),
            "body_follow_up_actions": IncidentFormAnswer(value="后续动作"),
            "body_timeline": IncidentFormAnswer(value=[{"time": "09:10", "event": "故障发生"}]),
        }
    )
    result, missing = build_report_data_from_snapshot(snapshot, strict_required=True)
    assert result is not None
    assert result["fault_date"] != ""
    assert result["reporting_person"] == "张三"
    assert result["detailed_description"] == "事故描述"
    assert len(result["event_sequence"]) >= 1
