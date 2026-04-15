from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .attachments import ChatAttachment
from ..skill.interaction import SkillInteractionStep


IncidentSessionStatus = Literal["draft", "generating", "generated", "failed"]


class IncidentFormAnswer(BaseModel):
    value: str | list[str] | None = Field(
        default=None,
        description="步骤值。single/text 为字符串，multi 为字符串数组。",
    )
    custom_value: str | None = Field(
        default=None,
        description="当步骤支持自定义输入时的补充值。",
    )


class IncidentReportSessionSnapshot(BaseModel):
    form_answers: dict[str, IncidentFormAnswer] = Field(
        default_factory=dict,
        description="表单各步骤的已填写答案。",
    )
    report_data: dict[str, Any] | None = Field(
        default=None,
        description="最终用于生成文档的 incident_data.json 内容。",
    )
    generated_attachment: ChatAttachment | None = Field(
        default=None,
        description="生成成功后的附件信息。",
    )
    generated_trace_id: str | None = Field(
        default=None,
        description="生成链路 trace_id，可用于回放。",
    )
    generated_at: datetime | None = Field(
        default=None,
        description="文档生成完成时间。",
    )
    is_locked: bool = Field(
        default=False,
        description="生成完成后表单锁定，不允许继续编辑。",
    )
    fallback_used: bool = Field(
        default=False,
        description="LLM 润色失败后是否回退到原始表单数据生成。",
    )
    polish_error: str | None = Field(
        default=None,
        description="LLM 润色失败原因，仅用于追踪展示。",
    )


class IncidentReportSessionSummary(BaseModel):
    id: str = Field(..., description="会话标识")
    title: str = Field(..., description="会话标题")
    status: IncidentSessionStatus = Field(default="draft", description="会话状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class IncidentReportSessionDetail(IncidentReportSessionSummary):
    snapshot: IncidentReportSessionSnapshot = Field(..., description="会话快照")


class IncidentReportSessionListResponse(BaseModel):
    sessions: list[IncidentReportSessionSummary] = Field(
        default_factory=list,
        description="事故报告历史会话列表",
    )


class IncidentReportSessionCreateRequest(BaseModel):
    title: str = Field(default="", description="会话标题")


class IncidentReportSessionUpdateRequest(BaseModel):
    snapshot: IncidentReportSessionSnapshot = Field(..., description="会话快照")


class IncidentReportSessionTitleUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, description="新的会话标题")


class IncidentReportGenerateRequest(BaseModel):
    model: str = Field(..., description="用于润色与生成的模型名称")
    reranker_model: str | None = Field(
        default=None,
        description="可选重排序模型；为空时回退为 model。",
    )
    output_name: str | None = Field(
        default=None,
        description="可选输出文件名；为空时按默认规则生成。",
    )


class IncidentReportGenerateResponse(BaseModel):
    session: IncidentReportSessionSummary = Field(..., description="更新后的会话摘要")
    snapshot: IncidentReportSessionSnapshot = Field(..., description="更新后的会话快照")
    trace_id: str = Field(
        ...,
        description="本次生成的 trace_id",
    )


class IncidentReportFormSchemaResponse(BaseModel):
    intro_message: str = Field(
        default="",
        description="欢迎向导文案。",
    )
    steps: list[SkillInteractionStep] = Field(
        default_factory=list,
        description="表单步骤定义。",
    )


def build_empty_incident_snapshot() -> IncidentReportSessionSnapshot:
    return IncidentReportSessionSnapshot(
        form_answers={},
        report_data=None,
        generated_attachment=None,
        generated_trace_id=None,
        generated_at=None,
        is_locked=False,
        fallback_used=False,
        polish_error=None,
    )

