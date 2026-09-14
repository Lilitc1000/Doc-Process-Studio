"""知识库 API 请求与响应 Schema。

形状与 RAGFlow 的数据模型对齐：项目 = dataset，文档 = dataset 内的 document。
本机不保存知识库业务数据，因此不存在"版本 / 是否最新 / 文件夹归属"这类本地概念。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KBProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


class KBProjectListResponse(BaseModel):
    projects: list[KBProjectResponse]


class KBDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    file_name: str
    file_type: str
    file_size: int = 0
    chunk_count: int = 0
    is_indexed: bool = False
    uploaded_at: datetime


class KBTreeNodeFolder(BaseModel):
    type: str = "folder"
    id: str
    name: str
    children: list["KBTreeNode"] = Field(default_factory=list)


class KBTreeNodeDocument(BaseModel):
    type: str = "document"
    id: str
    name: str
    file_type: str
    file_size: int = 0
    chunk_count: int = 0
    is_indexed: bool = False
    uploaded_at: datetime


KBTreeNode = KBTreeNodeFolder | KBTreeNodeDocument


class KBTreeResponse(BaseModel):
    project_id: str
    project_name: str
    tree: list[KBTreeNode]


class KBProjectSimpleItem(BaseModel):
    id: str
    name: str


class KBProjectListSimpleResponse(BaseModel):
    projects: list[KBProjectSimpleItem]


__all__ = [
    "KBDocumentResponse",
    "KBProjectListResponse",
    "KBProjectListSimpleResponse",
    "KBProjectResponse",
    "KBProjectSimpleItem",
    "KBTreeResponse",
    "KBTreeNode",
    "KBTreeNodeDocument",
    "KBTreeNodeFolder",
]
