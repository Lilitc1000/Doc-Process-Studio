from typing import Literal

from pydantic import BaseModel, Field

from ..models.incident_report import (
    IncidentReportSessionSnapshot,
    IncidentReportSessionSummary,
)
from ...skill.models.interaction import SkillInteractionStep


class IncidentBodyGenerateResponse(BaseModel):
    session: IncidentReportSessionSummary = Field(..., description="更新后的会话摘要")
    snapshot: IncidentReportSessionSnapshot = Field(..., description="更新后的会话快照")
    trace_id: str = Field(..., description="本次正文生成 trace_id。")
    section_id: str = Field(..., description="本次生成的分段标识。")
    timeline_index: int | None = Field(
        default=None,
        description="若为时间线条目生成，返回条目索引。",
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


class IncidentReportSessionListResponse(BaseModel):
    sessions: list[IncidentReportSessionSummary] = Field(
        default_factory=list,
        description="事故报告历史会话列表",
    )


class IncidentReportSessionDetail(IncidentReportSessionSummary):
    snapshot: IncidentReportSessionSnapshot = Field(..., description="会话快照")


class IncidentReportFormSchemaResponse(BaseModel):
    intro_message: str = Field(
        default="",
        description="欢迎向导文案。",
    )
    steps: list[SkillInteractionStep] = Field(
        default_factory=list,
        description="表单步骤定义。",
    )


__all__ = [
    "IncidentBodyGenerateResponse",
    "IncidentReportFormSchemaResponse",
    "IncidentReportPreviewResponse",
    "IncidentReportSessionDetail",
    "IncidentReportSessionListResponse",
]
