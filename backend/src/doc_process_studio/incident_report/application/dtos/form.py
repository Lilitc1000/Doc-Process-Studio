"""应用层表单 DTO。

包含表单答案快照、生成版本等跨层数据结构。
application 服务和 infrastructure 层共享这些 DTO 作为端口参数和返回类型。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IncidentFormAnswer(BaseModel):
    value: Any | None = Field(
        default=None,
        description="步骤值。支持字符串、列表、对象等结构。",
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
