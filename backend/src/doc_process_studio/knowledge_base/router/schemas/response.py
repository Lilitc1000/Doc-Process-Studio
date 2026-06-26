from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KBProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    folder_count: int = 0
    document_count: int = 0
    is_updating: bool = False
    last_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class KBProjectListResponse(BaseModel):
    projects: list[KBProjectResponse]


class KBFolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    parent_id: str | None = None
    name: str
    path: str
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class KBDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    folder_id: str | None = None
    file_name: str
    file_type: str
    file_size: int = 0
    chunk_count: int = 0
    version: int = 1
    is_indexed: bool = False
    is_latest: bool = True
    uploaded_at: datetime


class KBTreeNodeFolder(BaseModel):
    type: str = "folder"
    id: str
    name: str
    path: str
    sort_order: int = 0
    children: list["KBTreeNode"] = Field(default_factory=list)


class KBTreeNodeDocument(BaseModel):
    type: str = "document"
    id: str
    name: str
    file_type: str
    file_size: int = 0
    chunk_count: int = 0
    version: int = 1
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
    "KBFolderResponse",
    "KBProjectListResponse",
    "KBProjectListSimpleResponse",
    "KBProjectResponse",
    "KBProjectSimpleItem",
    "KBTreeNode",
    "KBTreeNodeDocument",
    "KBTreeNodeFolder",
    "KBTreeResponse",
]
