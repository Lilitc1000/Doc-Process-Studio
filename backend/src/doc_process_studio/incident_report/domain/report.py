"""事故报告聚合根。

封装报告的状态、状态转换、副作用字段计算、领域事件产出。
本模块零框架依赖，不 import SQLAlchemy / Pydantic / FastAPI。

状态转换行为：
- submit: draft/rejected → pending，设置 submitted_at
- approve: pending → approved，设置 verifier_id + approved_at
- reject: pending → rejected，设置 verifier_id
- assign_handler: approved/in_progress → in_progress（approved 推进），设置 assignee_id
- close: in_progress → closed，设置 closed_at + resolution_date
- reopen: closed → draft，清空 closed_at（不清 resolution_date）
- update_fields: 仅 draft/rejected 状态允许，不产生审计事件
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .errors import FormIncompleteError, InvalidTransitionError
from .events import (
    HandlerAssigned,
    ReportApproved,
    ReportClosed,
    ReportCreated,
    ReportEvent,
    ReportRejected,
    ReportReopened,
    ReportSubmitted,
)
from .form_validation import find_missing_submit_fields
from .permission import Permission
from .status import (
    ASSIGNABLE_STATUSES,
    EDITABLE_STATUSES,
    ReportStatus,
    can_transition,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class Report:
    """事故报告聚合根。"""

    # 身份与状态
    id: str
    ref_no: str
    title: str
    status: ReportStatus
    reporter_id: str
    # 参与人
    assignee_id: str | None = None
    verifier_id: str | None = None
    # 业务属性
    severity: str | None = None
    system: str | None = None
    site_id: str | None = None
    fault_date: datetime | None = None
    resolution_date: datetime | None = None
    form_data: dict[str, Any] = field(default_factory=dict)
    report_data: dict[str, Any] | None = None
    # 时间戳
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    closed_at: datetime | None = None
    # 领域事件（私有，应用层通过 consume_events 取出）
    _events: list[ReportEvent] = field(default_factory=list, repr=False)
    # 上一次转换前的状态（供事件记录 from_status）
    _prev_status: ReportStatus | None = field(default=None, repr=False)

    # ---- 工厂 ----
    @classmethod
    def create(
        cls,
        *,
        report_id: str,
        ref_no: str,
        title: str,
        reporter_id: str,
        severity: str | None = None,
        system: str | None = None,
        site_id: str | None = None,
        fault_date: datetime | None = None,
        form_data: dict[str, Any] | None = None,
    ) -> "Report":
        """创建新报告，初始状态为 draft，产生 ReportCreated 事件。"""
        report = cls(
            id=report_id,
            ref_no=ref_no,
            title=title,
            status=ReportStatus.DRAFT,
            reporter_id=reporter_id,
            severity=severity,
            system=system,
            site_id=site_id,
            fault_date=fault_date,
            form_data=form_data or {},
        )
        report._emit(
            ReportCreated,
            from_status=None,
            to_status=ReportStatus.DRAFT,
            actor_id=reporter_id,
        )
        return report

    # ---- 状态流转 ----
    def submit(self, *, actor_id: str, comment: str | None) -> None:
        """提交审核：draft/rejected → pending，设置 submitted_at。"""
        missing = find_missing_submit_fields(self.form_data)
        if missing:
            raise FormIncompleteError(missing)
        self._transition(ReportStatus.PENDING, action="submit")
        self.submitted_at = _utcnow()
        self._emit(
            ReportSubmitted,
            from_status=self._prev_status,
            to_status=ReportStatus.PENDING,
            actor_id=actor_id,
            comment=comment,
        )

    def approve(self, *, actor_id: str, comment: str | None) -> None:
        """审核通过：pending → approved，设置 verifier_id + approved_at。"""
        self._transition(ReportStatus.APPROVED, action="approve")
        self.verifier_id = actor_id
        self.approved_at = _utcnow()
        self._emit(
            ReportApproved,
            from_status=self._prev_status,
            to_status=ReportStatus.APPROVED,
            actor_id=actor_id,
            comment=comment,
        )

    def reject(self, *, actor_id: str, comment: str) -> None:
        """驳回：pending → rejected，设置 verifier_id。"""
        self._transition(ReportStatus.REJECTED, action="reject")
        self.verifier_id = actor_id
        self._emit(
            ReportRejected,
            from_status=self._prev_status,
            to_status=ReportStatus.REJECTED,
            actor_id=actor_id,
            comment=comment,
        )

    def assign_handler(
        self,
        *,
        actor_id: str,
        assignee_id: str,
        assignee_display: str,
    ) -> None:
        """分配处理人：approved → in_progress（推进），in_progress 保持不变。

        审计 comment 固定为 "分配处理人: {assignee_display}"，
        assignee_display 由应用层解析用户名后传入。
        """
        if self.status not in ASSIGNABLE_STATUSES:
            raise InvalidTransitionError(self.status.value, "assign", "仅 approved/in_progress 状态可分配")
        prev = self.status
        # approved 状态分配处理人时推进到 in_progress（原业务逻辑）
        if self.status == ReportStatus.APPROVED:
            self.status = ReportStatus.IN_PROGRESS
        self.assignee_id = assignee_id
        self.updated_at = _utcnow()
        self._emit(
            HandlerAssigned,
            from_status=prev,
            to_status=self.status,
            actor_id=actor_id,
            comment=f"分配处理人: {assignee_display}",
        )

    def close(self, *, actor_id: str, comment: str | None) -> None:
        """关闭：in_progress → closed，设置 closed_at + resolution_date。"""
        self._transition(ReportStatus.CLOSED, action="close")
        now = _utcnow()
        self.closed_at = now
        self.resolution_date = now
        self._emit(
            ReportClosed,
            from_status=self._prev_status,
            to_status=ReportStatus.CLOSED,
            actor_id=actor_id,
            comment=comment,
        )

    def reopen(self, *, actor_id: str, comment: str | None) -> None:
        """重新打开：closed → draft，清空 closed_at（不清 resolution_date）。"""
        self._transition(ReportStatus.DRAFT, action="reopen")
        self.closed_at = None
        self._emit(
            ReportReopened,
            from_status=self._prev_status,
            to_status=ReportStatus.DRAFT,
            actor_id=actor_id,
            comment=comment,
        )

    def update_fields(self, *, actor_id: str, **fields: Any) -> None:
        """更新报告字段：仅 draft/rejected 状态允许，不产生审计事件。

        跳过 None 值，不写审计日志。
        """
        if self.status not in EDITABLE_STATUSES:
            raise InvalidTransitionError(self.status.value, "edit", "仅 draft/rejected 状态可编辑")
        for key, value in fields.items():
            if not hasattr(self, key):
                continue
            if value is not None:
                setattr(self, key, value)
        self.updated_at = _utcnow()

    # ---- 所有权规则（编辑/查看权限分流）----
    def can_be_edited_by(self, user_id: str, permissions: set[Permission]) -> bool:
        """判断用户是否有权编辑此报告。

        权限规则：
        - report:edit_all → 可编辑任意报告
        - report:edit_own + 自己是报告人 → 可编辑
        - report:edit_assigned + 自己是处理人 → 可编辑
        """
        if Permission.REPORT_EDIT_ALL in permissions:
            return True
        if self.reporter_id == user_id and Permission.REPORT_EDIT_OWN in permissions:
            return True
        return self.assignee_id == user_id and Permission.REPORT_EDIT_ASSIGNED in permissions

    def is_visible_to(self, user_id: str, permissions: set[Permission]) -> bool:
        """判断用户是否有权查看此报告。

        权限规则：
        - report:view_all → 可查看任意报告
        - 否则仅能查看自己参与的报告（reporter/assignee/verifier）
        """
        if Permission.REPORT_VIEW_ALL in permissions:
            return True
        return user_id in (self.reporter_id, self.assignee_id, self.verifier_id)

    # ---- 事件 ----
    def consume_events(self) -> list[ReportEvent]:
        """取出并清空待处理的领域事件。"""
        events, self._events = self._events, []
        return events

    # ---- 私有 ----
    def _transition(self, target: ReportStatus, *, action: str) -> None:
        """校验状态转换合法性并推进状态。"""
        if not can_transition(self.status, target):
            raise InvalidTransitionError(self.status.value, action)
        self._prev_status = self.status
        self.status = target
        self.updated_at = _utcnow()

    def _emit(
        self,
        event_cls: type[ReportEvent],
        *,
        from_status: ReportStatus | None,
        to_status: ReportStatus,
        actor_id: str | None,
        comment: str | None = None,
    ) -> None:
        """追加领域事件。"""
        self._events.append(
            event_cls(
                report_id=self.id,
                actor_id=actor_id,
                from_status=from_status.value if from_status else None,
                to_status=to_status.value,
                comment=comment,
            )
        )
