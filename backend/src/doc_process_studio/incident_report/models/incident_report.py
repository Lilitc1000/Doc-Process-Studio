from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from ...chat.models.attachment import ChatAttachment
from ...skill.models.interaction import SkillInteractionStep

IncidentSessionStatus = Literal["draft", "generating", "generated", "failed"]


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
    attachment: ChatAttachment = Field(..., description="该版本对应附件。")
    report_data: dict[str, Any] = Field(
        default_factory=dict,
        description="该版本生成时使用的 report_data 快照。",
    )


class IncidentReportSessionSnapshot(BaseModel):
    form_answers: dict[str, IncidentFormAnswer] = Field(
        default_factory=dict,
        description="表单各步骤的已填写答案。",
    )
    report_data: dict[str, Any] | None = Field(
        default=None,
        description="最近一次用于生成文档的 report_data 内容。",
    )
    generated_attachment: ChatAttachment | None = Field(
        default=None,
        description="最近一次生成成功后的附件信息。",
    )
    generated_versions: list[IncidentGeneratedVersion] = Field(
        default_factory=list,
        description="历史生成版本列表（含附件与数据快照）。",
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


class IncidentReportSessionSummary(BaseModel):
    id: str = Field(..., description="会话标识")
    title: str = Field(..., description="会话标题")
    status: IncidentSessionStatus = Field(default="draft", description="会话状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


def build_empty_incident_snapshot() -> IncidentReportSessionSnapshot:
    return IncidentReportSessionSnapshot(
        form_answers={},
        report_data=None,
        generated_attachment=None,
        generated_versions=[],
        generated_trace_id=None,
        section_trace_ids={},
        generated_at=None,
        polish_error=None,
    )
