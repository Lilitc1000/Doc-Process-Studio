from datetime import UTC, datetime

from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
from doc_process_studio.incident_report.service.report_store import (
    _CLEAR_SENTINEL,
    orm_to_detail,
    orm_to_summary,
)


def _make_report(**overrides) -> IncidentReport:
    now = datetime.now(UTC)
    defaults = dict(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status="draft",
        severity="P2",
        reporter_id="usr_test",
        assignee_id=None,
        verifier_id=None,
        system="数据库",
        site_id="SITE-01",
        fault_date=now,
        resolution_date=None,
        form_data={"key": "value"},
        report_data=None,
        created_at=now,
        updated_at=now,
        submitted_at=None,
        approved_at=None,
        closed_at=None,
    )
    defaults.update(overrides)
    return IncidentReport(**defaults)


def test_orm_to_summary_maps_fields():
    report = _make_report()
    summary = orm_to_summary(report)
    assert summary.id == "rep-1"
    assert summary.ref_no == "DAS-0001"
    assert summary.title == "测试报告"
    assert summary.status == "draft"
    assert summary.severity == "P2"
    assert summary.reporter_id == "usr_test"
    assert summary.reporter_name is None
    assert summary.assignee_id is None
    assert summary.assignee_name is None
    assert summary.verifier_id is None
    assert summary.verifier_name is None
    assert summary.fault_date is not None
    assert summary.created_at is not None
    assert summary.updated_at is not None


def test_orm_to_detail_maps_fields():
    report = _make_report()
    detail = orm_to_detail(report)
    assert detail.id == "rep-1"
    assert detail.system == "数据库"
    assert detail.site_id == "SITE-01"
    assert detail.form_data == {"key": "value"}
    assert detail.report_data is None
    assert detail.submitted_at is None
    assert detail.approved_at is None
    assert detail.closed_at is None
    assert detail.resolution_date is None


def test_orm_to_detail_with_all_fields():
    now = datetime.now(UTC)
    report = _make_report(
        assignee_id="usr_handler",
        verifier_id="usr_verifier",
        submitted_at=now,
        approved_at=now,
        closed_at=now,
        resolution_date=now,
        report_data={"severity": "P2"},
    )
    detail = orm_to_detail(report)
    assert detail.assignee_id == "usr_handler"
    assert detail.verifier_id == "usr_verifier"
    assert detail.submitted_at is not None
    assert detail.approved_at is not None
    assert detail.closed_at is not None
    assert detail.resolution_date is not None
    assert detail.report_data == {"severity": "P2"}


def test_clear_sentinel_is_unique():
    assert _CLEAR_SENTINEL is not None
    assert _CLEAR_SENTINEL is not False
    sentinel2 = object()
    assert _CLEAR_SENTINEL is not sentinel2


def test_orm_to_summary_with_none_severity():
    report = _make_report(severity=None)
    summary = orm_to_summary(report)
    assert summary.severity is None


def test_orm_to_detail_empty_form_data():
    report = _make_report(form_data=None)
    detail = orm_to_detail(report)
    assert detail.form_data == {}
