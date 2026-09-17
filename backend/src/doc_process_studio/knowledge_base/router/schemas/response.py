"""知识库 API 请求与响应 Schema。

结构形状（项目 / 文档 / 树节点 / 轻量项）定义在应用层 ``application.dtos``，
本模块只做 API 包装与**再导出**：既避免同一份结构维护两遍，也避免应用层
反向依赖路由层造成循环导入。
"""

from pydantic import BaseModel

from ...application.dtos import (
    KBDocument,
    KBDocumentParseDetail,
    KBProject,
    KBProjectSimpleItem,
    KBTreeNodeDocument,
    KBTreeNodeFolder,
)
from ...application.dtos import KBTreeNode as _KBTreeNode

# API 契约沿用旧名，既有导入方无需改动
KBProjectResponse = KBProject
KBDocumentResponse = KBDocument
KBDocumentParseDetailResponse = KBDocumentParseDetail
KBTreeNode = _KBTreeNode


class KBProjectListResponse(BaseModel):
    projects: list[KBProjectResponse]


class KBProjectListSimpleResponse(BaseModel):
    projects: list[KBProjectSimpleItem]


class KBTreeResponse(BaseModel):
    project_id: str
    project_name: str
    tree: list[KBTreeNode]


__all__ = [
    "KBDocumentParseDetailResponse",
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
