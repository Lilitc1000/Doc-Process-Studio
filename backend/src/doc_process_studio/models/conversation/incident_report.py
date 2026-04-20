from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .attachments import ChatAttachment
from ..skill.interaction import SkillInteractionStep


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
    is_locked: bool = Field(
        default=False,
        description="兼容旧字段，当前始终为 false。",
    )
    fallback_used: bool = Field(
        default=False,
        description="兼容旧字段，当前纯表单附件生成链路不使用。",
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


class IncidentBodyQuickGenerateRequest(BaseModel):
    model: str = Field(..., description="用于正文生成的模型名称")
    reranker_model: str | None = Field(
        default=None,
        description="可选重排序模型；为空时回退为 model。",
    )


class IncidentBodySectionGenerateRequest(BaseModel):
    model: str = Field(..., description="用于正文润色的模型名称")
    reranker_model: str | None = Field(
        default=None,
        description="可选重排序模型；为空时回退为 model。",
    )
    section_id: str = Field(..., description="正文分段标识。")
    timeline_index: int | None = Field(
        default=None,
        description="当 section_id 为 timeline_item 时，指定时间线条目索引。",
    )


class IncidentBodyGenerateResponse(BaseModel):
    session: IncidentReportSessionSummary = Field(..., description="更新后的会话摘要")
    snapshot: IncidentReportSessionSnapshot = Field(..., description="更新后的会话快照")
    trace_id: str = Field(..., description="本次正文生成 trace_id。")
    section_id: str = Field(..., description="本次生成的分段标识。")
    timeline_index: int | None = Field(
        default=None,
        description="若为时间线条目生成，返回条目索引。",
    )


class IncidentReportPreviewRequest(BaseModel):
    version: int | None = Field(
        default=None,
        description="要预览的历史版本号；为空时预览当前草稿。",
    )
    model: str | None = Field(
        default=None,
        description="可选模型名称；用于草稿预览时的英文翻译。",
    )
    reranker_model: str | None = Field(
        default=None,
        description="可选重排序模型；为空时回退为 model。",
    )


class IncidentReportPreviewResponse(BaseModel):
    source: Literal["draft", "version"] = Field(..., description="预览来源。")
    version: int | None = Field(default=None, description="历史版本号。")
    label: str = Field(..., description="预览标签。")
    html: str = Field(..., description="转换后的 HTML 预览内容。")
    docx_base64: str | None = Field(
        default=None,
        description="可选 DOCX 文档内容（base64 编码，草稿预览下载使用）。",
    )
    docx_file_name: str | None = Field(
        default=None,
        description="草稿预览下载文件名。",
    )
    pdf_base64: str | None = Field(
        default=None,
        description="可选 PDF 预览内容（base64 编码）。",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="文档转 HTML 的提示信息。",
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
        generated_versions=[],
        generated_trace_id=None,
        section_trace_ids={},
        generated_at=None,
        is_locked=False,
        fallback_used=False,
        polish_error=None,
    )
