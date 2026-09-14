"""CompositeReferenceContext 单元测试。

覆盖：纯事实章节跳过检索、启用章节拼接素材、检索异常/无命中降级、英文 query 构造。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from doc_process_studio.incident_report.application.ports import (
    KnowledgeChunk,
    ReferenceContextPort,
)
from doc_process_studio.incident_report.infrastructure.adapters.reference_context import (
    CompositeReferenceContext,
    _build_retrieval_query,
)

ENABLED_SECTIONS = "quick,impact,root_cause,follow_up"


class _FakeBase(ReferenceContextPort):
    def __init__(self, text: str = "[base] reference") -> None:
        self.text = text

    async def resolve(
        self,
        *,
        model: str,
        section_id: str,
        timeline_index: int | None,
        prompt: str,
        context_json: str,
    ) -> tuple[str, list[str], str]:
        # 测试桩：固定返回，忽略入参；参数名须与端口签名一致以匹配关键字调用。
        del model, section_id, timeline_index, prompt, context_json
        return self.text, ["body-sections/common.md"], "heuristic"


def _chunk(content: str, doc_id: str = "d1", score: float = 0.9) -> KnowledgeChunk:
    return KnowledgeChunk(
        content=content,
        scope="history",
        source="report.md",
        document_id=doc_id,
        score=score,
    )


async def test_description_section_skips_knowledge() -> None:
    base = _FakeBase()
    retriever = AsyncMock()
    comp = CompositeReferenceContext(
        base=base,
        retriever=retriever,
        ragflow_enabled_sections=ENABLED_SECTIONS,
        ragflow_top_k=3,
    )
    text, files, reason = await comp.resolve(
        model="m",
        section_id="description",
        timeline_index=None,
        prompt="p",
        context_json="{}",
    )
    assert text == "[base] reference"
    retriever.retrieve.assert_not_called()


async def test_timeline_section_skips_knowledge() -> None:
    base = _FakeBase()
    retriever = AsyncMock()
    comp = CompositeReferenceContext(
        base=base,
        retriever=retriever,
        ragflow_enabled_sections=ENABLED_SECTIONS,
        ragflow_top_k=3,
    )
    text, _, _ = await comp.resolve(
        model="m",
        section_id="timeline_item",
        timeline_index=0,
        prompt="p",
        context_json="{}",
    )
    assert text == "[base] reference"
    retriever.retrieve.assert_not_called()


async def test_impact_section_appends_material() -> None:
    base = _FakeBase()
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(return_value=[_chunk("NAS2 shutdown at 20:35 due to I/O overload")])
    comp = CompositeReferenceContext(
        base=base,
        retriever=retriever,
        ragflow_enabled_sections=ENABLED_SECTIONS,
        ragflow_top_k=3,
    )
    text, files, reason = await comp.resolve(
        model="m",
        section_id="impact",
        timeline_index=None,
        prompt="p",
        context_json='{"asset":"NAS2"}',
    )
    assert "[RAGFlow report.md]" in text
    assert "NAS2 shutdown at 20:35 due to I/O overload" in text
    assert "ragflow:1 chunks" in reason
    retriever.retrieve.assert_awaited_once()


async def test_retriever_exception_degrades_to_base() -> None:
    base = _FakeBase()
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(side_effect=RuntimeError("boom"))
    comp = CompositeReferenceContext(
        base=base,
        retriever=retriever,
        ragflow_enabled_sections=ENABLED_SECTIONS,
        ragflow_top_k=3,
    )
    text, files, reason = await comp.resolve(
        model="m",
        section_id="impact",
        timeline_index=None,
        prompt="p",
        context_json="{}",
    )
    assert text == "[base] reference"
    assert "ragflow:error" in reason


async def test_no_hits_keeps_base_with_reason() -> None:
    base = _FakeBase()
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(return_value=[])
    comp = CompositeReferenceContext(
        base=base,
        retriever=retriever,
        ragflow_enabled_sections=ENABLED_SECTIONS,
        ragflow_top_k=3,
    )
    text, files, reason = await comp.resolve(
        model="m",
        section_id="quick",
        timeline_index=None,
        prompt="p",
        context_json="{}",
    )
    assert text == "[base] reference"
    assert "ragflow:no_hits" in reason


async def test_base_exception_does_not_propagate() -> None:
    retriever = AsyncMock()
    comp = CompositeReferenceContext(
        base=_FakeBase(),
        retriever=retriever,
        ragflow_enabled_sections=ENABLED_SECTIONS,
        ragflow_top_k=3,
    )
    # 强制 base.resolve 抛异常，composite 应降级为空 base 而非崩溃
    comp._base = AsyncMock()
    comp._base.resolve = AsyncMock(side_effect=RuntimeError("base down"))
    text, _, _ = await comp.resolve(
        model="m",
        section_id="impact",
        timeline_index=None,
        prompt="p",
        context_json="{}",
    )
    assert text.startswith("[fallback]")


def test_query_builder_uses_english_and_entities() -> None:
    q = _build_retrieval_query(
        section_id="impact",
        context_json='{"manual_fault_description":"NAS 故障","asset":"NAS1","note":"中文备注"}',
    )
    assert "impact" in q.lower() or "incident" in q.lower()
    assert "NAS1" in q
    assert "中文" not in q  # 中文不直接进入英文 query


def test_query_builder_bad_json_falls_back_to_topic() -> None:
    q = _build_retrieval_query(section_id="root_cause", context_json="not-json")
    assert "root cause" in q.lower()
