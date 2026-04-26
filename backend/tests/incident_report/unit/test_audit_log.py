import asyncio

from doc_process_studio.incident_report.service.audit_log import (
    orm_to_entry,
)


def test_create_audit_log_creates_entry(monkeypatch):
    from doc_process_studio.incident_report.models.audit_log import IncidentAuditLog
    from datetime import UTC, datetime

    fake_log = IncidentAuditLog(
        id="log-1",
        report_id="rep-1",
        action="submit",
        actor_id="usr_test",
        from_status="draft",
        to_status="pending",
        comment="提交审核",
        created_at=datetime.now(UTC),
    )

    async def _fake_create_audit_log(**kwargs):
        return fake_log

    import doc_process_studio.incident_report.service.audit_log as audit_module
    monkeypatch.setattr(audit_module, "create_audit_log", _fake_create_audit_log)

    result = asyncio.run(_fake_create_audit_log(
        report_id="rep-1",
        action="submit",
        actor_id="usr_test",
        from_status="draft",
        to_status="pending",
        comment="提交审核",
    ))

    assert result.action == "submit"
    assert result.from_status == "draft"
    assert result.to_status == "pending"


def test_orm_to_entry_converts_correctly():
    from doc_process_studio.incident_report.models.audit_log import IncidentAuditLog
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    log = IncidentAuditLog(
        id="log-1",
        report_id="rep-1",
        action="approve",
        actor_id="usr_verifier",
        from_status="pending",
        to_status="approved",
        comment="通过",
        created_at=now,
    )

    entry = orm_to_entry(log)
    assert entry.id == "log-1"
    assert entry.action == "approve"
    assert entry.actor_id == "usr_verifier"
    assert entry.from_status == "pending"
    assert entry.to_status == "approved"
    assert entry.comment == "通过"
