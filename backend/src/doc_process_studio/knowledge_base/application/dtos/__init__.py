"""知识库应用层数据结构。

这里定义知识库的**结构形状**（项目 / 文档 / 树节点）与**检索形状**（命中片段），
供 application 与 infrastructure 共用；router 层只做 API 包装与再导出。

分层纪律：application / infrastructure 只依赖本模块，**不得**反向依赖
``router.schemas``——否则会形成循环导入（ports -> router -> kb_service -> ports）。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KBProject(BaseModel):
    """知识库项目（= RAGFlow dataset）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


# RAGFlow 文档 run 字段的取值
PARSE_UNSTART = "UNSTART"
PARSE_RUNNING = "RUNNING"
PARSE_DONE = "DONE"
PARSE_FAIL = "FAIL"


class KBDocument(BaseModel):
    """知识库文档（= RAGFlow dataset 内的 document）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    file_name: str
    file_type: str
    file_size: int = 0
    chunk_count: int = 0
    is_indexed: bool = False
    parse_status: str = PARSE_UNSTART
    uploaded_at: datetime


class KBTreeNodeFolder(BaseModel):
    """树节点：文件夹。RAGFlow 侧 folder 只读，前端不提供写入口。"""

    type: str = "folder"
    id: str
    name: str
    children: list["KBTreeNode"] = Field(default_factory=list)


class KBTreeNodeDocument(BaseModel):
    """树节点：文档。"""

    type: str = "document"
    id: str
    name: str
    file_type: str
    file_size: int = 0
    chunk_count: int = 0
    is_indexed: bool = False
    parse_status: str = PARSE_UNSTART
    uploaded_at: datetime


KBTreeNode = KBTreeNodeFolder | KBTreeNodeDocument


class KBProjectSimpleItem(BaseModel):
    """对话 ``$`` 提及用的轻量项目项。"""

    id: str
    name: str


class KBProjectTree(BaseModel):
    """某个项目的目录树（应用层形状，router 层再包装成 API 响应）。"""

    project_id: str
    project_name: str
    tree: list[KBTreeNode]


class KBDocumentParseDetail(BaseModel):
    """单个文档的解析详情（供前端弹窗按需拉取）。

    ``message`` 是 RAGFlow 的 ``progress_msg``，包含分阶段日志与 ``[ERROR]`` 原因，
    可能很长，因此不随列表/树返回。
    """

    document_id: str
    file_name: str
    parse_status: str = PARSE_UNSTART
    is_indexed: bool = False
    progress: float = 0.0
    chunk_count: int = 0
    token_count: int = 0
    process_duration: float | None = None
    message: str = ""
    updated_at: datetime | None = None


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
    "KBDocument",
    "KBDocumentParseDetail",
    "KBIndexHit",
    "KBIndexResult",
    "KBProject",
    "KBProjectSimpleItem",
    "KBProjectTree",
    "KBTreeNode",
    "KBTreeNodeDocument",
    "KBTreeNodeFolder",
]
