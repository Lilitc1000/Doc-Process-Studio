import asyncio
from datetime import UTC, datetime

import pytest

from doc_process_studio.incident_report.service.report import (
    assign_handler,
    delete_report,
    get_report,
    list_incident_reports,
    reopen_report,
    submit_report,
    update_report,
)
from doc_process_studio.incident_report.service.report_store import _CLEAR_SENTINEL


class _FakeCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


def _apply_fields(target, fields):
    for k, v in fields.items():
        if v is _CLEAR_SENTINEL:
            setattr(target, k, None)
        else:
            setattr(target, k, v)


def test_update_report_rejects_non_editable_status(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="pending",
        reporter_id="usr_test", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)

    with pytest.raises(ValueError, match="不允许编辑"):
        asyncio.run(update_report(report_id="rep-1", user_id="usr_test", title="new"))


def test_update_report_non_owner_non_admin_rejected(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_other", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return False

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    with pytest.raises(ValueError, match="无权编辑此报告"):
        asyncio.run(update_report(report_id="rep-1", user_id="usr_test", title="new"))


def test_update_report_admin_can_edit_others(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_other", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return True

    async def _fake_update(report_id, **fields):
        _apply_fields(fake_report, fields)
        return fake_report

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)
    monkeypatch.setattr(report_module, "update_report_record", _fake_update)

    result = asyncio.run(update_report(report_id="rep-1", user_id="usr_admin", title="updated"))
    assert result is not None


def test_submit_report_non_owner_non_admin_rejected(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_other", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return False

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    with pytest.raises(ValueError, match="需要报告人权限才能提交审核"):
        asyncio.run(submit_report(report_id="rep-1", actor_id="usr_test"))


def test_submit_report_wrong_status(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="approved",
        reporter_id="usr_test", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    with pytest.raises(ValueError, match="不允许提交审核"):
        asyncio.run(submit_report(report_id="rep-1", actor_id="usr_test"))


def test_approve_report_wrong_status(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_test", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    with pytest.raises(ValueError, match="不允许审核通过"):
        asyncio.run(report_module.approve_report(report_id="rep-1", actor_id="usr_verifier"))


def test_reject_report_wrong_status(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_test", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    with pytest.raises(ValueError, match="不允许驳回"):
        asyncio.run(report_module.reject_report(report_id="rep-1", actor_id="usr_verifier", comment="no"))


def test_assign_handler_wrong_status(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_test", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    with pytest.raises(ValueError, match="不允许分配处理人"):
        asyncio.run(assign_handler(report_id="rep-1", actor_id="usr_admin", assignee_id="usr_handler"))


def test_close_report_wrong_status(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_test", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    with pytest.raises(ValueError, match="不允许关闭"):
        asyncio.run(report_module.close_report(report_id="rep-1", actor_id="usr_handler"))


def test_reopen_report_wrong_status(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_test", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_load(report_id):
        return fake_report if report_id == "rep-1" else None

    async def _fake_has_permission(user_id, permission):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    with pytest.raises(ValueError, match="不允许重新打开"):
        asyncio.run(reopen_report(report_id="rep-1", actor_id="usr_admin"))


def test_get_report_returns_none_for_missing(monkeypatch):
    async def _fake_load(report_id):
        return None

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "load_report_orm", _fake_load)

    result = asyncio.run(get_report("nonexistent"))
    assert result is None


def test_delete_report_with_actor_creates_audit(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=MagicMock())
    mock_session.execute = AsyncMock(return_value=MagicMock())
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    async def _fake_has_permission(user_id, permission):
        return True

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "async_session_factory", lambda: _FakeCtx(mock_session))
    monkeypatch.setattr(report_module, "has_permission", _fake_has_permission)

    result = asyncio.run(delete_report(report_id="rep-1", actor_id="usr_admin"))
    assert result is True
    mock_session.delete.assert_called_once()
    mock_session.commit.assert_called_once()


def test_delete_report_without_actor_skips_audit(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=MagicMock())
    mock_session.execute = AsyncMock(return_value=MagicMock())
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "async_session_factory", lambda: _FakeCtx(mock_session))

    result = asyncio.run(delete_report(report_id="rep-1"))
    assert result is True
    mock_session.delete.assert_called_once()
    mock_session.commit.assert_called_once()


def test_list_incident_reports(monkeypatch):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
    from doc_process_studio.incident_report.schemas.response import IncidentReportListResponse

    now = datetime.now(UTC)
    fake_report = IncidentReport(
        id="rep-1", ref_no="DAS-0001", title="测试", status="draft",
        reporter_id="usr_test", form_data={}, created_at=now, updated_at=now,
    )

    async def _fake_list_reports(**kwargs):
        return [fake_report], 1

    import doc_process_studio.incident_report.service.report as report_module
    monkeypatch.setattr(report_module, "list_reports", _fake_list_reports)

    result = asyncio.run(list_incident_reports())
    assert isinstance(result, IncidentReportListResponse)
    assert result.total == 1
    assert len(result.items) == 1
