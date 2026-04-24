from pydantic import BaseModel, Field

from ..models.incident_report import IncidentReportSessionSnapshot


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


__all__ = [
    "IncidentBodyQuickGenerateRequest",
    "IncidentBodySectionGenerateRequest",
    "IncidentReportPreviewRequest",
    "IncidentReportSessionCreateRequest",
    "IncidentReportSessionTitleUpdateRequest",
    "IncidentReportSessionUpdateRequest",
]
