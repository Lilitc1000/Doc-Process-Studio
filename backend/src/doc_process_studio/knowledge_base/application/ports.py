"""知识库应用层端口。

知识库以 **RAGFlow 为唯一真相源**：应用里的"项目"就是 RAGFlow 的 dataset，
文件夹与文档全部由 RAGFlow 派生，本机不再保存任何知识库业务数据。

因此本端口既是"结构网关"（项目 / 文件夹 / 文档），也是"检索网关"（``search``），
二者共用同一份 RAGFlow 事实，不再各自维护一套目录。
"""

from abc import ABC, abstractmethod

from .dtos import (
    KBDocument,
    KBDocumentParseDetail,
    KBIndexHit,
    KBProject,
    KBTreeNode,
)


class KnowledgeBaseRepository(ABC):
    """知识库网关端口。

    纪律：
    - 读路径遇到未配置 / 网络异常 / 资源不存在时返回空容器，**不抛异常**，
      由调用方转成 404 或空列表；
    - 写路径失败返回 ``None`` / ``False``，由调用方转成对应错误码；
    - 实现方不得在本机持久化知识库业务数据（全部落在 RAGFlow）。
    """

    @abstractmethod
    async def list_projects(self) -> list[KBProject]:
        """列出全部项目（= RAGFlow dataset）。"""

    @abstractmethod
    async def get_project(self, project_id: str) -> KBProject | None:
        """按 dataset id 取项目；不存在返回 ``None``。"""

    @abstractmethod
    async def create_project(self, name: str, description: str = "") -> KBProject:
        """新建项目（在 RAGFlow 建 dataset）。"""

    @abstractmethod
    async def rename_project(self, project_id: str, new_name: str) -> KBProject | None:
        """重命名项目；不存在返回 ``None``。"""

    @abstractmethod
    async def delete_project(self, project_id: str) -> bool:
        """删除项目（连同 RAGFlow dataset）；不存在返回 ``False``。"""

    @abstractmethod
    async def list_simple_projects(self) -> list[dict[str, str]]:
        """供对话 ``$`` 提及使用的轻量列表 ``[{"id","name"}]``。"""

    @abstractmethod
    async def build_tree(self, project_id: str) -> list[KBTreeNode]:
        """构建项目内的文件夹 / 文档树。

        dataset 无文件夹时返回扁平文档列表，有文件夹时返回层级树——由实现方
        依据 RAGFlow 返回的文件夹数据派生，调用方无需感知。
        """

    @abstractmethod
    async def upload_document(
        self,
        project_id: str,
        file_name: str,
        file_bytes: bytes,
    ) -> KBDocument | None:
        """上传文档并在 RAGFlow 侧触发解析 / 切块。

        压缩包会先在本地解包，逐个成员上传；返回最后一份文档的元数据。
        """

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """删除文档；不存在返回 ``False``。"""

    @abstractmethod
    async def get_document_parse_detail(self, document_id: str) -> KBDocumentParseDetail | None:
        """取单个文档的解析详情；不存在返回 ``None``。"""

    @abstractmethod
    async def trigger_document_parse(self, document_id: str) -> bool:
        """对已上传文档（重新）触发解析 / 切片；定位不到文档返回 ``False``。"""

    @abstractmethod
    async def search(
        self,
        *,
        project_id: str,
        query: str,
        top_k: int | None = None,
    ) -> list[KBIndexHit]:
        """在单个 dataset 内检索；未配置 / 异常时返回空列表。"""
