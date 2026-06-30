"""Report 聚合根单元测试。

覆盖状态机全部分支、副作用字段、领域事件产出、权限规则。
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from doc_process_studio.incident_report.domain.entities.report import Report
from doc_process_studio.incident_report.domain.entities.status import ReportStatus
from doc_process_studio.incident_report.domain.events import (
    HandlerAssigned,
    ReportApproved,
    ReportClosed,
    ReportCreated,
    ReportReopened,
    ReportSubmitted,
)
from doc_process_studio.incident_report.domain.values.errors import (
    FormIncompleteError,
    InvalidTransitionError,
)
from doc_process_studio.incident_report.domain.values.permission import Permission


def _make_report(**overrides: Any) -> Report:
    """构造测试用 Report 聚合根。"""
    defaults: dict[str, Any] = dict(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status=ReportStatus.DRAFT,
        reporter_id="usr_reporter",
    )
    defaults.update(overrides)
    return Report(**defaults)


def _full_form_data() -> dict[str, Any]:
    """构造完整的表单数据（提交校验通过）。"""
    return {
        "manual_fault_date": "2026-01-01",
        "manual_reporting_person": "张三",
        "manual_site_id": "site-1",
        "manual_system": "system-1",
        "manual_fault_symptom": "故障描述",
    }


# ---- 工厂方法 ----
class TestReportCreate:
    def test_create_sets_draft_status(self) -> None:
        report = Report.create(
            report_id="rep-1",
            ref_no="DAS-0001",
            title="测试",
            reporter_id="usr_1",
        )
        assert report.status == ReportStatus.DRAFT
        assert report.reporter_id == "usr_1"

    def test_create_produces_created_event(self) -> None:
        report = Report.create(
            report_id="rep-1",
            ref_no="DAS-0001",
            title="测试",
            reporter_id="usr_1",
        )
        events = report.consume_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportCreated)
        assert events[0].action == "create"
        assert events[0].from_status is None
        assert events[0].to_status == "draft"
        assert events[0].actor_id == "usr_1"


# ---- submit ----
class TestReportSubmit:
    def test_submit_from_draft_to_pending(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT, form_data=_full_form_data())
        report.submit(actor_id="usr_1", comment=None)
        assert report.status == ReportStatus.PENDING
        assert report.submitted_at is not None

    def test_submit_from_rejected_to_pending(self) -> None:
        report = _make_report(status=ReportStatus.REJECTED, form_data=_full_form_data())
        report.submit(actor_id="usr_1", comment="重新提交")
        assert report.status == ReportStatus.PENDING

    def test_submit_from_pending_raises(self) -> None:
        report = _make_report(status=ReportStatus.PENDING, form_data=_full_form_data())
        with pytest.raises(InvalidTransitionError):
            report.submit(actor_id="usr_1", comment=None)

    def test_submit_with_missing_fields_raises(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT, form_data={})
        with pytest.raises(FormIncompleteError) as exc:
            report.submit(actor_id="usr_1", comment=None)
        assert "manual_fault_date" in exc.value.missing

    def test_submit_produces_submitted_event(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT, form_data=_full_form_data())
        report.submit(actor_id="usr_1", comment="提交备注")
        events = report.consume_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportSubmitted)
        assert events[0].action == "submit"
        assert events[0].from_status == "draft"
        assert events[0].to_status == "pending"
        assert events[0].comment == "提交备注"


# ---- approve ----
class TestReportApprove:
    def test_approve_from_pending_to_approved(self) -> None:
        report = _make_report(status=ReportStatus.PENDING)
        report.approve(actor_id="usr_verifier", comment=None)
        assert report.status == ReportStatus.APPROVED
        assert report.verifier_id == "usr_verifier"
        assert report.approved_at is not None

    def test_approve_from_draft_raises(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT)
        with pytest.raises(InvalidTransitionError):
            report.approve(actor_id="usr_verifier", comment=None)

    def test_approve_produces_approved_event(self) -> None:
        report = _make_report(status=ReportStatus.PENDING)
        report.approve(actor_id="usr_verifier", comment="通过")
        events = report.consume_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportApproved)
        assert events[0].action == "approve"
        assert events[0].from_status == "pending"
        assert events[0].to_status == "approved"


# ---- reject ----
class TestReportReject:
    def test_reject_from_pending_to_rejected(self) -> None:
        report = _make_report(status=ReportStatus.PENDING)
        report.reject(actor_id="usr_verifier", comment="不通过")
        assert report.status == ReportStatus.REJECTED
        assert report.verifier_id == "usr_verifier"

    def test_reject_from_draft_raises(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT)
        with pytest.raises(InvalidTransitionError):
            report.reject(actor_id="usr_verifier", comment="不通过")


# ---- assign_handler ----
class TestReportAssignHandler:
    def test_assign_from_approved_advances_to_in_progress(self) -> None:
        report = _make_report(status=ReportStatus.APPROVED)
        report.assign_handler(
            actor_id="usr_verifier",
            assignee_id="usr_handler",
        )
        assert report.status == ReportStatus.IN_PROGRESS
        assert report.assignee_id == "usr_handler"

    def test_assign_from_in_progress_keeps_status(self) -> None:
        report = _make_report(status=ReportStatus.IN_PROGRESS, assignee_id="usr_old")
        report.assign_handler(
            actor_id="usr_verifier",
            assignee_id="usr_new",
        )
        assert report.status == ReportStatus.IN_PROGRESS
        assert report.assignee_id == "usr_new"

    def test_assign_from_draft_raises(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT)
        with pytest.raises(InvalidTransitionError):
            report.assign_handler(
                actor_id="usr_verifier",
                assignee_id="usr_handler",
            )

    def test_assign_event_has_no_comment(self) -> None:
        report = _make_report(status=ReportStatus.APPROVED)
        report.assign_handler(
            actor_id="usr_verifier",
            assignee_id="usr_handler",
        )
        events = report.consume_events()
        assert len(events) == 1
        assert isinstance(events[0], HandlerAssigned)
        assert events[0].action == "assign"
        assert events[0].from_status == "approved"
        assert events[0].to_status == "in_progress"
        assert events[0].comment is None


# ---- close ----
class TestReportClose:
    def test_close_from_in_progress_to_closed(self) -> None:
        report = _make_report(status=ReportStatus.IN_PROGRESS)
        report.close(actor_id="usr_handler", comment=None)
        assert report.status == ReportStatus.CLOSED
        assert report.closed_at is not None
        assert report.resolution_date is not None

    def test_close_from_draft_raises(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT)
        with pytest.raises(InvalidTransitionError):
            report.close(actor_id="usr_handler", comment=None)

    def test_close_produces_closed_event(self) -> None:
        report = _make_report(status=ReportStatus.IN_PROGRESS)
        report.close(actor_id="usr_handler", comment="已解决")
        events = report.consume_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportClosed)
        assert events[0].action == "close"
        assert events[0].from_status == "in_progress"
        assert events[0].to_status == "closed"


# ---- reopen ----
class TestReportReopen:
    def test_reopen_from_closed_to_draft(self) -> None:
        report = _make_report(
            status=ReportStatus.CLOSED,
            closed_at=datetime.now(UTC),
            resolution_date=datetime.now(UTC),
        )
        report.reopen(actor_id="usr_admin", comment=None)
        assert report.status == ReportStatus.DRAFT
        assert report.closed_at is None
        # reopen 不清 resolution_date
        assert report.resolution_date is not None

    def test_reopen_from_draft_raises(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT)
        with pytest.raises(InvalidTransitionError):
            report.reopen(actor_id="usr_admin", comment=None)

    def test_reopen_produces_reopened_event(self) -> None:
        report = _make_report(status=ReportStatus.CLOSED)
        report.reopen(actor_id="usr_admin", comment="重新打开")
        events = report.consume_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportReopened)
        assert events[0].action == "reopen"
        assert events[0].from_status == "closed"
        assert events[0].to_status == "draft"


# ---- update_fields ----
class TestReportUpdateFields:
    def test_update_in_draft_allowed(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT)
        report.update_fields(title="新标题", severity="P1")
        assert report.title == "新标题"
        assert report.severity == "P1"

    def test_update_in_rejected_allowed(self) -> None:
        report = _make_report(status=ReportStatus.REJECTED)
        report.update_fields(title="新标题")
        assert report.title == "新标题"

    def test_update_in_pending_raises(self) -> None:
        report = _make_report(status=ReportStatus.PENDING)
        with pytest.raises(InvalidTransitionError):
            report.update_fields(title="新标题")

    def test_update_skips_none_values(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT, title="原标题")
        report.update_fields(title=None, severity="P1")
        # None 值被跳过，不覆盖原值
        assert report.title == "原标题"
        assert report.severity == "P1"

    def test_update_does_not_produce_event(self) -> None:
        """update 仅修改字段，不产生审计事件。"""
        report = _make_report(status=ReportStatus.DRAFT)
        report.update_fields(title="新标题")
        assert report.consume_events() == []


# ---- 权限规则 ----
class TestReportPermissions:
    def test_can_be_edited_by_reporter_with_edit_own(self) -> None:
        report = _make_report(reporter_id="usr_1")
        assert report.can_be_edited_by("usr_1", {Permission.REPORT_EDIT_OWN}) is True

    def test_can_be_edited_by_assignee_with_edit_assigned(self) -> None:
        report = _make_report(assignee_id="usr_2")
        assert report.can_be_edited_by("usr_2", {Permission.REPORT_EDIT_ASSIGNED}) is True

    def test_can_be_edited_by_admin_with_edit_all(self) -> None:
        report = _make_report(reporter_id="usr_1")
        assert report.can_be_edited_by("usr_admin", {Permission.REPORT_EDIT_ALL}) is True

    def test_cannot_be_edited_without_permission(self) -> None:
        report = _make_report(reporter_id="usr_1")
        assert report.can_be_edited_by("usr_2", set()) is False

    def test_is_visible_to_participant(self) -> None:
        report = _make_report(reporter_id="usr_1")
        assert report.is_visible_to("usr_1", set()) is True

    def test_is_visible_to_non_participant_without_view_all(self) -> None:
        report = _make_report(reporter_id="usr_1")
        assert report.is_visible_to("usr_2", set()) is False

    def test_is_visible_to_with_view_all(self) -> None:
        report = _make_report(reporter_id="usr_1")
        assert report.is_visible_to("usr_2", {Permission.REPORT_VIEW_ALL}) is True


# ---- 事件消费 ----
class TestEventConsumption:
    def test_consume_events_clears_queue(self) -> None:
        report = Report.create(report_id="rep-1", ref_no="DAS-0001", title="t", reporter_id="usr_1")
        assert len(report.consume_events()) == 1
        assert report.consume_events() == []

    def test_multiple_transitions_produce_multiple_events(self) -> None:
        report = _make_report(status=ReportStatus.DRAFT, form_data=_full_form_data())
        report.submit(actor_id="usr_1", comment=None)
        report.approve(actor_id="usr_v", comment=None)
        report.assign_handler(actor_id="usr_v", assignee_id="usr_h")
        report.close(actor_id="usr_h", comment=None)
        events = report.consume_events()
        assert len(events) == 4  # submit + approve + assign + close
        assert isinstance(events[0], ReportSubmitted)
        assert isinstance(events[1], ReportApproved)
        assert isinstance(events[2], HandlerAssigned)
        assert isinstance(events[3], ReportClosed)
