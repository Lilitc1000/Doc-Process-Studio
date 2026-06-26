from doc_process_studio.incident_report.application.dtos import (
    IncidentFormAnswer,
    IncidentFormSnapshot,
    build_empty_form_snapshot,
)
from doc_process_studio.incident_report.domain.entities.status import TRANSITIONS, ReportStatus
from doc_process_studio.incident_report.domain.values.permission import (
    INCIDENT_VALID_ROLES,
    VALID_ROLES,
)
from doc_process_studio.incident_report.domain.values.status_types import (
    VALID_SEVERITIES,
    VALID_STATUSES,
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
    assert sorted(VALID_ROLES) == INCIDENT_VALID_ROLES


def test_status_transitions_draft():
    assert TRANSITIONS[ReportStatus.DRAFT] == {ReportStatus.PENDING}


def test_status_transitions_rejected():
    assert TRANSITIONS[ReportStatus.REJECTED] == {ReportStatus.PENDING}


def test_status_transitions_pending():
    assert TRANSITIONS[ReportStatus.PENDING] == {ReportStatus.APPROVED, ReportStatus.REJECTED}


def test_status_transitions_approved():
    assert TRANSITIONS[ReportStatus.APPROVED] == {ReportStatus.IN_PROGRESS}


def test_status_transitions_in_progress():
    assert TRANSITIONS[ReportStatus.IN_PROGRESS] == {ReportStatus.CLOSED}


def test_status_transitions_closed():
    assert TRANSITIONS[ReportStatus.CLOSED] == {ReportStatus.DRAFT}


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
