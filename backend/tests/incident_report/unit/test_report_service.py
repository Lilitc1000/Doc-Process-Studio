import asyncio
from datetime import UTC, datetime

import pytest

from doc_process_studio.incident_report.service.report import (
    create_report,
    submit_report,
    approve_report,
    reject_report,
    close_report,
    reopen_report,
    assign_handler,
)
from doc_process_studio.incident_report.service.report_store import (
    _CLEAR_SENTINEL,
    generate_ref_no,
    orm_to_detail,
    orm_to_summary,
)


def _apply_fields(target, fields):
    for k, v in fields.items():
        if v is _CLEAR_SENTINEL:
            setattr(target, k, None)
        else:
            setattr(target, k, v)


def test_create_report_sets_default_status(monkeypatch):
    async def _fake_generate_ref_no():
        return "DAS-0001"

    async def _fake_create_report_record(**kwargs):
        from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
        now = datetime.now(UTC)
        return IncidentReport(
            id=kwargs["report_id"],
            ref_no=kwargs["ref_no"],
            title=kwargs["title"],
            status="draft",
            severity=kwargs.get("severity"),
            reporter_id=kwargs["reporter_id"],
            system=kwargs.get("system"),
            site_id=kwargs.get("site_id"),
            fault_date=kwargs.get("fault_date"),
            form_data=kwargs.get("form_data") or {},
            created_at=now,
            updated_at=now,
        )

    async def _fake_create_audit_log(**kwargs):
        from doc_process_studio.incident_report.models.audit_log import IncidentAuditLog
        return IncidentAuditLog(
            id="log-1",
            report_id=kwargs["report_id"],
            action=kwargs["action"],
            actor_id=kwargs["actor_id"],
            to_status=kwargs.get("to_status"),
            created_at=datetime.now(UTC),
        )

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "generate_ref_no", _fake_generate_ref_no)
    monkeypatch.setattr(report_module, "create_report_record", _fake_create_report_record)
    monkeypatch.setattr(report_module, "create_audit_log", _fake_create_audit_log)

    report = asyncio.run(create_report(
        title="测试报告",
        reporter_id="usr_test",
    ))

    assert report.status == "draft"
    assert report.ref_no.startswith("DAS-")


def test_submit_report_changes_status_to_pending(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status="draft",
        reporter_id="usr_test",
        form_data={},
        created_at=now,
        updated_at=now,
    )

    async def _fake_load_report_orm(report_id):
        if report_id == "rep-1":
            return fake_report
        return None

    async def _fake_update_report_record(report_id, **fields):
        _apply_fields(fake_report, fields)
        return fake_report

    async def _fake_create_audit_log(**kwargs):
        from doc_process_studio.incident_report.models.audit_log import IncidentAuditLog
        return IncidentAuditLog(
            id="log-1",
            report_id=kwargs["report_id"],
            action=kwargs["action"],
            actor_id=kwargs["actor_id"],
            created_at=datetime.now(UTC),
        )

    async def _fake_has_incident_role(user_id, role):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load_report_orm)
    monkeypatch.setattr(report_module, "update_report_record", _fake_update_report_record)
    monkeypatch.setattr(report_module, "create_audit_log", _fake_create_audit_log)

    result = asyncio.run(submit_report(
        report_id="rep-1",
        actor_id="usr_test",
    ))
    assert result.status == "pending"


def test_approve_report_changes_status_to_approved(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status="pending",
        reporter_id="usr_test",
        form_data={},
        created_at=now,
        updated_at=now,
    )

    async def _fake_load_report_orm(report_id):
        if report_id == "rep-1":
            return fake_report
        return None

    async def _fake_update_report_record(report_id, **fields):
        _apply_fields(fake_report, fields)
        return fake_report

    async def _fake_create_audit_log(**kwargs):
        from doc_process_studio.incident_report.models.audit_log import IncidentAuditLog
        return IncidentAuditLog(
            id="log-1",
            report_id=kwargs["report_id"],
            action=kwargs["action"],
            actor_id=kwargs["actor_id"],
            created_at=datetime.now(UTC),
        )

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load_report_orm)
    monkeypatch.setattr(report_module, "update_report_record", _fake_update_report_record)
    monkeypatch.setattr(report_module, "create_audit_log", _fake_create_audit_log)

    result = asyncio.run(approve_report(
        report_id="rep-1",
        actor_id="usr_verifier",
        comment="通过",
    ))
    assert result.status == "approved"


def test_reject_report_changes_status_to_rejected(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status="pending",
        reporter_id="usr_test",
        form_data={},
        created_at=now,
        updated_at=now,
    )

    async def _fake_load_report_orm(report_id):
        if report_id == "rep-1":
            return fake_report
        return None

    async def _fake_update_report_record(report_id, **fields):
        _apply_fields(fake_report, fields)
        return fake_report

    async def _fake_create_audit_log(**kwargs):
        from doc_process_studio.incident_report.models.audit_log import IncidentAuditLog
        return IncidentAuditLog(
            id="log-1",
            report_id=kwargs["report_id"],
            action=kwargs["action"],
            actor_id=kwargs["actor_id"],
            created_at=datetime.now(UTC),
        )

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load_report_orm)
    monkeypatch.setattr(report_module, "update_report_record", _fake_update_report_record)
    monkeypatch.setattr(report_module, "create_audit_log", _fake_create_audit_log)

    result = asyncio.run(reject_report(
        report_id="rep-1",
        actor_id="usr_verifier",
        comment="信息不完整",
    ))
    assert result.status == "rejected"


def test_close_report_changes_status_to_closed(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status="in_progress",
        reporter_id="usr_test",
        assignee_id="usr_handler",
        form_data={},
        created_at=now,
        updated_at=now,
    )

    async def _fake_load_report_orm(report_id):
        if report_id == "rep-1":
            return fake_report
        return None

    async def _fake_update_report_record(report_id, **fields):
        _apply_fields(fake_report, fields)
        return fake_report

    async def _fake_create_audit_log(**kwargs):
        from doc_process_studio.incident_report.models.audit_log import IncidentAuditLog
        return IncidentAuditLog(
            id="log-1",
            report_id=kwargs["report_id"],
            action=kwargs["action"],
            actor_id=kwargs["actor_id"],
            created_at=datetime.now(UTC),
        )

    async def _fake_has_incident_role(user_id, role):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load_report_orm)
    monkeypatch.setattr(report_module, "update_report_record", _fake_update_report_record)
    monkeypatch.setattr(report_module, "create_audit_log", _fake_create_audit_log)

    result = asyncio.run(close_report(
        report_id="rep-1",
        actor_id="usr_handler",
    ))
    assert result.status == "closed"


def test_reopen_report_changes_status_to_draft(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status="closed",
        reporter_id="usr_test",
        form_data={},
        created_at=now,
        updated_at=now,
    )

    async def _fake_load_report_orm(report_id):
        if report_id == "rep-1":
            return fake_report
        return None

    async def _fake_update_report_record(report_id, **fields):
        _apply_fields(fake_report, fields)
        return fake_report

    async def _fake_create_audit_log(**kwargs):
        from doc_process_studio.incident_report.models.audit_log import IncidentAuditLog
        return IncidentAuditLog(
            id="log-1",
            report_id=kwargs["report_id"],
            action=kwargs["action"],
            actor_id=kwargs["actor_id"],
            created_at=datetime.now(UTC),
        )

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load_report_orm)
    monkeypatch.setattr(report_module, "update_report_record", _fake_update_report_record)
    monkeypatch.setattr(report_module, "create_audit_log", _fake_create_audit_log)

    result = asyncio.run(reopen_report(
        report_id="rep-1",
        actor_id="usr_admin",
    ))
    assert result.status == "draft"
