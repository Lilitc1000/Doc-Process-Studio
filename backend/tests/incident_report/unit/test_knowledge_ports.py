"""KnowledgeChunk / KnowledgeRetrieverPort 端口定义测试。"""

from __future__ import annotations

from doc_process_studio.incident_report.application.ports import (
    KnowledgeChunk,
    KnowledgeRetrieverPort,
)


def test_knowledge_chunk_is_frozen_and_constructible() -> None:
    chunk = KnowledgeChunk(
        content="NAS2 shutdown at 20:35",
        scope="history",
        source="report.md",
        document_id="d1",
        score=0.87,
    )
    assert chunk.content == "NAS2 shutdown at 20:35"
    assert chunk.scope == "history"
    assert chunk.document_id == "d1"
    # frozen dataclass：不可变
    try:
        chunk.score = 0.1  # type: ignore[misc]
    except Exception:
        pass
    else:  # pragma: no cover - 依赖 frozen 语义
        raise AssertionError("KnowledgeChunk 应为 frozen")


def test_knowledge_retriever_port_is_abstract() -> None:
    assert KnowledgeRetrieverPort.__abstractmethods__  # 含 retrieve
