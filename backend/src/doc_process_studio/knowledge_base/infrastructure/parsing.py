"""文档类型识别工具。

从 ``documents.py`` 抽出，用于在把原文件交给索引实现（RAGFlow 服务端）前
判断文件类型与是否为压缩包。
"""

from pathlib import PurePosixPath

_FILE_TYPE_MAP = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
}

_ARCHIVE_SUFFIXES = {".zip", ".rar", ".7z"}


def detect_file_type(file_name: str) -> str:
    """按扩展名判断文件类型，不支持时返回空串。"""
    return _FILE_TYPE_MAP.get(PurePosixPath(file_name).suffix.lower(), "")


def is_archive(file_name: str) -> bool:
    return PurePosixPath(file_name).suffix.lower() in _ARCHIVE_SUFFIXES
