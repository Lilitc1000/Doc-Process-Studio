from doc_process_studio.incident_report.schemas.common import (
    INCIDENT_VALID_ROLES,
    STATUS_TRANSITIONS,
    VALID_ROLES,
    VALID_SEVERITIES,
    VALID_STATUSES,
    IncidentFormAnswer,
    IncidentFormSnapshot,
    build_empty_form_snapshot,
)


def test_valid_statuses():
    assert "draft" in VALID_STATUSES
    assert "pending" in VALID_STATUSES
    assert "approved" in VALID_STATUSES
    assert "rejected" in VALID_STATUSES
    assert "in_progress" in VALID_STATUSES
    assert "closed" in VALID_STATUSES


def test_valid_severities():
    assert "P0" in VALID_SEVERITIES
    assert "P1" in VALID_SEVERITIES
    assert "P2" in VALID_SEVERITIES
    assert "P3" in VALID_SEVERITIES


def test_valid_roles():
    assert "reporter" in VALID_ROLES
    assert "handler" in VALID_ROLES
    assert "verifier" in VALID_ROLES
    assert "admin" in VALID_ROLES
    assert "viewer" in VALID_ROLES


def test_incident_valid_roles_sorted():
    assert INCIDENT_VALID_ROLES == sorted(VALID_ROLES)


def test_status_transitions_draft():
    assert STATUS_TRANSITIONS["draft"] == {"pending"}


def test_status_transitions_rejected():
    assert STATUS_TRANSITIONS["rejected"] == {"pending"}


def test_status_transitions_pending():
    assert STATUS_TRANSITIONS["pending"] == {"approved", "rejected"}


def test_status_transitions_approved():
    assert STATUS_TRANSITIONS["approved"] == {"in_progress"}


def test_status_transitions_in_progress():
    assert STATUS_TRANSITIONS["in_progress"] == {"closed"}


def test_status_transitions_closed():
    assert STATUS_TRANSITIONS["closed"] == {"draft"}


def test_incident_form_answer_defaults():
    answer = IncidentFormAnswer()
    assert answer.value is None
    assert answer.custom_value is None


def test_incident_form_answer_with_value():
    answer = IncidentFormAnswer(value="test", custom_value="custom")
    assert answer.value == "test"
    assert answer.custom_value == "custom"


def test_incident_form_snapshot_defaults():
    snapshot = IncidentFormSnapshot()
    assert snapshot.form_answers == {}
    assert snapshot.report_data is None
    assert snapshot.generated_trace_id is None
    assert snapshot.section_trace_ids == {}
    assert snapshot.generated_at is None
    assert snapshot.polish_error is None


def test_build_empty_form_snapshot():
    snapshot = build_empty_form_snapshot()
    assert snapshot.form_answers == {}
    assert snapshot.report_data is None
    assert snapshot.generated_trace_id is None
