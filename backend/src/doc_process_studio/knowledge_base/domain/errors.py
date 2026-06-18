"""知识库领域异常。

所有知识库业务错误继承 KnowledgeBaseError，应用层抛出后由 router 映射为 HTTP 状态码。
"""


class KnowledgeBaseError(Exception):
    """知识库域异常基类。"""


class ProjectNotFoundError(KnowledgeBaseError):
    """知识库项目不存在。"""


class FolderNotFoundError(KnowledgeBaseError):
    """文件夹不存在。"""


class DocumentNotFoundError(KnowledgeBaseError):
    """文档不存在。"""


class UnsupportedFileTypeError(KnowledgeBaseError):
    """不支持的文件格式或项目不存在。"""


class FileTooLargeError(KnowledgeBaseError):
    """文件大小超过上传限制。"""
