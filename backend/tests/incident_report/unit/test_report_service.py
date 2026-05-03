import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from doc_process_studio.incident_report.service.report import (
    create_report,
    submit_report,
    approve_report,
    reject_report,
    close_report,
    reopen_report,
)


def _make_orm_report(**overrides):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
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
        system=None,
        site_id=None,
        fault_date=None,
        form_data={},
        report_data=None,
        created_at=now,
        updated_at=now,
        submitted_at=None,
        approved_at=None,
        closed_at=None,
        resolution_date=None,
    )
    defaults.update(overrides)
    return IncidentReport(**defaults)


def test_create_report_sets_default_status():
    fake_record = _make_orm_report()

    with patch(
        "doc_process_studio.incident_report.service.report.has_permission",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "doc_process_studio.incident_report.service.report.create_report_record",
        new_callable=AsyncMock,
        return_value=fake_record,
    ), patch(
        "doc_process_studio.incident_report.service.report.create_audit_log",
        new_callable=AsyncMock,
    ), patch(
        "doc_process_studio.incident_report.service.report.orm_to_detail",
        new_callable=AsyncMock,
        return_value=MagicMock(status="draft", ref_no="DAS-0001"),
    ):
        result = asyncio.run(create_report(
            title="测试报告",
            reporter_id="usr_test",
        ))

    assert result.status == "draft"
    assert result.ref_no.startswith("DAS-")


def test_submit_report_changes_status_to_pending():
    fake_report = _make_orm_report(status="draft")

    with patch(
        "doc_process_studio.incident_report.service.report.load_report_orm",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.update_report_record",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.create_audit_log",
        new_callable=AsyncMock,
    ), patch(
        "doc_process_studio.incident_report.service.report.orm_to_detail",
        new_callable=AsyncMock,
        return_value=MagicMock(status="pending"),
    ), patch(
        "doc_process_studio.incident_report.service.report.has_permission",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "doc_process_studio.incident_report.service.report.validate_form_data_for_submit",
        return_value=[],
    ):
        result = asyncio.run(submit_report(
            report_id="rep-1",
            actor_id="usr_test",
        ))
    assert result.status == "pending"


def test_approve_report_changes_status_to_approved():
    fake_report = _make_orm_report(status="pending")

    with patch(
        "doc_process_studio.incident_report.service.report.has_permission",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "doc_process_studio.incident_report.service.report.load_report_orm",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.update_report_record",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.create_audit_log",
        new_callable=AsyncMock,
    ), patch(
        "doc_process_studio.incident_report.service.report.orm_to_detail",
        new_callable=AsyncMock,
        return_value=MagicMock(status="approved"),
    ):
        result = asyncio.run(approve_report(
            report_id="rep-1",
            actor_id="usr_verifier",
            comment="通过",
        ))
    assert result.status == "approved"


def test_reject_report_changes_status_to_rejected():
    fake_report = _make_orm_report(status="pending")

    with patch(
        "doc_process_studio.incident_report.service.report.has_permission",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "doc_process_studio.incident_report.service.report.load_report_orm",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.update_report_record",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.create_audit_log",
        new_callable=AsyncMock,
    ), patch(
        "doc_process_studio.incident_report.service.report.orm_to_detail",
        new_callable=AsyncMock,
        return_value=MagicMock(status="rejected"),
    ):
        result = asyncio.run(reject_report(
            report_id="rep-1",
            actor_id="usr_verifier",
            comment="信息不完整",
        ))
    assert result.status == "rejected"


def test_close_report_changes_status_to_closed():
    fake_report = _make_orm_report(status="in_progress", assignee_id="usr_handler")

    with patch(
        "doc_process_studio.incident_report.service.report.load_report_orm",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.update_report_record",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.create_audit_log",
        new_callable=AsyncMock,
    ), patch(
        "doc_process_studio.incident_report.service.report.orm_to_detail",
        new_callable=AsyncMock,
        return_value=MagicMock(status="closed"),
    ), patch(
        "doc_process_studio.incident_report.service.report.has_permission",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = asyncio.run(close_report(
            report_id="rep-1",
            actor_id="usr_handler",
        ))
    assert result.status == "closed"


def test_reopen_report_changes_status_to_draft():
    fake_report = _make_orm_report(status="closed")

    with patch(
        "doc_process_studio.incident_report.service.report.has_permission",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "doc_process_studio.incident_report.service.report.load_report_orm",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.update_report_record",
        new_callable=AsyncMock,
        return_value=fake_report,
    ), patch(
        "doc_process_studio.incident_report.service.report.create_audit_log",
        new_callable=AsyncMock,
    ), patch(
        "doc_process_studio.incident_report.service.report.orm_to_detail",
        new_callable=AsyncMock,
        return_value=MagicMock(status="draft"),
    ):
        result = asyncio.run(reopen_report(
            report_id="rep-1",
            actor_id="usr_admin",
        ))
    assert result.status == "draft"
