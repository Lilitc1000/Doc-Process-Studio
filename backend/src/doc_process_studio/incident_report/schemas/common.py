from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

IncidentReportStatus = Literal["draft", "pending", "approved", "rejected", "in_progress", "closed"]
IncidentSeverity = Literal["P0", "P1", "P2", "P3"]

VALID_STATUSES: set[str] = {"draft", "pending", "approved", "rejected", "in_progress", "closed"}
VALID_SEVERITIES: set[str] = {"P0", "P1", "P2", "P3"}
VALID_ROLES: set[str] = {"reporter", "handler", "verifier", "admin", "viewer"}
INCIDENT_VALID_ROLES: list[str] = sorted(VALID_ROLES)

STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending"},
    "rejected": {"pending"},
    "pending": {"approved", "rejected"},
    "approved": {"in_progress"},
    "in_progress": {"closed"},
    "closed": {"draft"},
}


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class IncidentFormAnswer(BaseModel):
    value: Any | None = Field(
        default=None,
        description="步骤值。支持字符串、列表、对象等结构。",
    )
    custom_value: str | None = Field(
        default=None,
        description="当步骤支持自定义输入时的补充值。",
    )


class IncidentGeneratedVersion(BaseModel):
    version: int = Field(..., description="版本号，从 1 开始递增。")
    label: str = Field(..., description="用于前端展示的版本标签。")
    generated_at: datetime = Field(..., description="该版本生成时间。")
    report_data: dict[str, Any] = Field(
        default_factory=dict,
        description="该版本生成时使用的 report_data 快照。",
    )


class IncidentFormSnapshot(BaseModel):
    form_answers: dict[str, IncidentFormAnswer] = Field(
        default_factory=dict,
        description="表单各步骤的已填写答案。",
    )
    report_data: dict[str, Any] | None = Field(
        default=None,
        description="最近一次用于生成文档的 report_data 内容。",
    )
    generated_trace_id: str | None = Field(
        default=None,
        description="最近一次正文 AI 生成链路 trace_id，可用于回放。",
    )
    section_trace_ids: dict[str, str] = Field(
        default_factory=dict,
        description="正文分段生成对应的 trace_id。",
    )
    generated_at: datetime | None = Field(
        default=None,
        description="最近一次文档生成完成时间。",
    )
    polish_error: str | None = Field(
        default=None,
        description="最近一次正文 AI 生成失败原因（如有）。",
    )


def build_empty_form_snapshot() -> IncidentFormSnapshot:
    return IncidentFormSnapshot(
        form_answers={},
        report_data=None,
        generated_trace_id=None,
        section_trace_ids={},
        generated_at=None,
        polish_error=None,
    )
