"""知识库应用层数据结构。

仅保留检索相关的形状；项目 / 文件夹 / 文档的统一形状由 ``router.schemas``
定义（那里同时承担 API 契约），避免同一份结构维护两遍。
"""

from pydantic import BaseModel, Field


class KBIndexHit(BaseModel):
    """一次检索命中的片段（与具体索引实现无关的统一形状）。"""

    content: str = Field(default="", description="片段文本")
    score: float = Field(default=0.0, description="相似度/得分")
    document_id: str = Field(default="", description="命中的文档 ID（RAGFlow 文档 ID）")
    source: str = Field(default="", description="来源展示名（通常是文档名）")
    file_name: str = Field(default="", description="文件名")


class KBIndexResult(BaseModel):
    """上传 + 解析的结果。

    ``success=False`` 表示解析未成功；文档仍可能已经存在于 RAGFlow 中，
    调用方应据此标记"未索引"以便重试，但**不得**阻断上传主流程。
    """

    success: bool = Field(default=False, description="是否解析成功")
    chunk_count: int = Field(default=0, description="切块数量（解析异步进行，允许暂为 0）")
    external_document_id: str = Field(default="", description="RAGFlow 返回的文档 ID")
    message: str = Field(default="", description="失败原因摘要，用于日志")


__all__ = [
    "KBIndexHit",
    "KBIndexResult",
]
