"""知识库分层纪律测试。

守住两条底线：

1. 知识库不保存本地业务数据——模块里不得出现 SQLAlchemy ORM / 会话依赖；
2. 知识库读写一律经 ``KnowledgeBaseRepository`` 端口，业务代码不直连 RAGFlow 客户端。
"""

import ast
from pathlib import Path

import pytest

_MODULE_ROOT = Path("src/doc_process_studio/knowledge_base")
if not _MODULE_ROOT.exists():
    _MODULE_ROOT = Path("backend/src/doc_process_studio/knowledge_base")

_FORBIDDEN_IMPORTS = {
    "sqlalchemy",
    "sqlalchemy.orm",
    "sqlalchemy.ext.asyncio",
}


def _python_files() -> list[Path]:
    return sorted(_MODULE_ROOT.rglob("*.py"))


def test_knowledge_base_module_exists() -> None:
    assert _MODULE_ROOT.exists(), "找不到 knowledge_base 模块，测试路径可能不在仓库根目录"


def test_no_sqlalchemy_imports_in_knowledge_base() -> None:
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name.split(".")[0] == "sqlalchemy" or name in _FORBIDDEN_IMPORTS for name in names):
                offenders.append(str(path))
    assert offenders == [], f"知识库不应再依赖 SQLAlchemy：{offenders}"


def test_repository_port_is_the_only_gateway() -> None:
    """``application`` 层可以依赖公共基础设施（配置等），但不得直连本模块的基础设施实现。"""
    offenders: list[str] = []
    for path in (_MODULE_ROOT / "application").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "knowledge_base.infrastructure" in node.module:
                offenders.append(f"{path}:{node.module}")
    assert offenders == [], f"应用层不得直连知识库基础设施：{offenders}"


def test_ragflow_client_is_used_only_by_repository() -> None:
    """RAGFlow 客户端只允许被仓储持有，以及依赖装配层用来构造仓储。"""
    allowed = {"ragflow_repository.py", "dependencies.py"}
    offenders: list[str] = []
    for path in _python_files():
        if path.name in allowed:
            continue
        if "ragflow_client" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    assert offenders == [], f"RAGFlow 客户端只应由仓储持有：{offenders}"


@pytest.mark.parametrize("module", ["persistence", "kb_repository", "ragflow_index"])
def test_local_persistence_modules_are_gone(module: str) -> None:
    """本地 KB 持久化模块必须整包移除（只留缓存目录不影响判定）。"""
    target = _MODULE_ROOT / "infrastructure" / module
    assert not (_MODULE_ROOT / "infrastructure" / f"{module}.py").exists()
    assert not (target.is_dir() and list(target.rglob("*.py"))), f"{target} 仍有 Python 源码"
