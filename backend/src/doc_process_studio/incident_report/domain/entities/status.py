"""事故报告状态机定义。

本模块是状态转换规则的唯一事实源，所有状态校验都查询 TRANSITIONS。
"""

from enum import StrEnum


class ReportStatus(StrEnum):
    """事故报告状态。"""

    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


# 状态转换规则：当前状态 → 允许的目标状态集合
# 这是状态机的唯一事实源，所有状态校验都查询此表。
TRANSITIONS: dict[ReportStatus, set[ReportStatus]] = {
    ReportStatus.DRAFT: {ReportStatus.PENDING},
    ReportStatus.REJECTED: {ReportStatus.PENDING},
    ReportStatus.PENDING: {ReportStatus.APPROVED, ReportStatus.REJECTED},
    ReportStatus.APPROVED: {ReportStatus.IN_PROGRESS},
    ReportStatus.IN_PROGRESS: {ReportStatus.CLOSED},
    ReportStatus.CLOSED: {ReportStatus.DRAFT},
}


def can_transition(current: ReportStatus, target: ReportStatus) -> bool:
    """判断从 current 到 target 的状态转换是否合法。"""
    return target in TRANSITIONS.get(current, set())


# 允许编辑的状态集合（update_report 的状态校验用此表）
EDITABLE_STATUSES: frozenset[ReportStatus] = frozenset(
    {
        ReportStatus.DRAFT,
        ReportStatus.REJECTED,
    }
)

# 允许分配处理人的状态集合（assign_handler 的状态校验用此表）
ASSIGNABLE_STATUSES: frozenset[ReportStatus] = frozenset(
    {
        ReportStatus.APPROVED,
        ReportStatus.IN_PROGRESS,
    }
)
