"""CompositeReferenceContext 单元测试。

覆盖：纯事实章节跳过检索、启用章节拼接素材、检索异常/无命中降级、英文 query 构造。

RAGFLOW 配置（启用章节 / 召回条数）已改为运行期从 ``RagflowConfigProvider`` 解析，
因此这里用 ``_FakeProvider`` 提供一份确定性的 ``RagflowConfig``。
"""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock

from doc_process_studio.incident_report.application.ports import (
    KnowledgeChunk,
    ReferenceContextPort,
)
from doc_process_studio.incident_report.infrastructure.adapters.reference_context import (
    CompositeReferenceContext,
    _build_retrieval_query,
)
from doc_process_studio.settings.application.ports import RagflowConfigProvider
from doc_process_studio.settings.domain.values import RagflowConfig, SecretSource

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


class _FakeProvider(RagflowConfigProvider):
    def __init__(
        self,
        *,
        enabled_sections: str = ENABLED_SECTIONS,
        top_k: int = 3,
        base_url: str = "",
        api_key: str = "",
        enabled: bool = False,
    ) -> None:
        self._config = RagflowConfig(
            base_url=base_url,
            api_key=api_key,
            enabled=enabled,
            source=SecretSource.NONE,
            enabled_sections=enabled_sections,
            top_k=top_k,
        )

    async def resolve(self, *, scope: str = "system") -> RagflowConfig:
        del scope  # 伪造实现：匹配真实 Provider 的签名，测试中忽略该参数
        return self._config

    def invalidate(self, *, scope: str | None = None) -> None:
        del scope  # 伪造实现：无缓存，无需失效


def _chunk(content: str, doc_id: str = "d1", score: float = 0.9) -> KnowledgeChunk:
    return KnowledgeChunk(
        content=content,
        scope="history",
        source="report.md",
        document_id=doc_id,
        score=score,
    )


def _composite(
    retriever: AsyncMock,
    *,
    enabled_sections: str = ENABLED_SECTIONS,
    top_k: int = 3,
) -> CompositeReferenceContext:
    return CompositeReferenceContext(
        base=_FakeBase(),
        retriever=retriever,
        config_provider=_FakeProvider(enabled_sections=enabled_sections, top_k=top_k),
    )


async def test_description_section_skips_knowledge() -> None:
    retriever = AsyncMock()
    comp = _composite(retriever)
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
    retriever = AsyncMock()
    comp = _composite(retriever)
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
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(return_value=[_chunk("NAS2 shutdown at 20:35 due to I/O overload")])
    comp = _composite(retriever)
    text, files, reason = await comp.resolve(
        model="m",
        section_id="impact",
        timeline_index=None,
        prompt="p",
        context_json='{"asset":"NAS2"}',
    )
    assert "[RAGFlow · report.md]" in text
    assert "NAS2 shutdown at 20:35 due to I/O overload" in text
    assert "ragflow:1 chunks" in reason
    retriever.retrieve.assert_awaited_once_with(query=ANY, scope="history", top_k=3)


async def test_material_block_carries_usage_notice() -> None:
    """注入的素材必须带「仅作写法参考、禁止照抄事实」声明。

    背景：素材描述的是其他事故。没有这条声明时，模型会把历史报告里的
    设备编号、时间戳、交易笔数照抄进新报告，产出看似翔实但全假的内容。
    """
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(return_value=[_chunk("NAS2 shutdown at 20:35")])
    comp = _composite(retriever)
    text, _, _ = await comp.resolve(
        model="m",
        section_id="impact",
        timeline_index=None,
        prompt="p",
        context_json="{}",
    )
    assert "structure and terminology reference only" in text
    assert "Never copy" in text
    assert "OTHER incidents" in text


async def test_retriever_exception_degrades_to_base() -> None:
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(side_effect=RuntimeError("boom"))
    comp = _composite(retriever)
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
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(return_value=[])
    comp = _composite(retriever)
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
    comp = _composite(retriever)
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


async def test_disabled_section_is_skipped() -> None:
    """enabled_sections 不含当前章节时，即使 retriever 可用也不应检索。"""
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(return_value=[_chunk("x")])
    comp = _composite(retriever, enabled_sections="impact")
    text, _, _ = await comp.resolve(
        model="m",
        section_id="quick",
        timeline_index=None,
        prompt="p",
        context_json="{}",
    )
    assert text == "[base] reference"
    retriever.retrieve.assert_not_called()


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


def test_query_builder_prefers_system_domain() -> None:
    """表单 system 字段是结构化检索键，应优先于从文本抽取的 token。

    背景：原先只抽 ASCII token，中文口语输入抽不出内容，query 退化为纯主题词，
    检索结果与本次事故无关，甚至跨域召回存储域因果链。
    """
    q_database = _build_retrieval_query(
        section_id="root_cause",
        context_json='{"manual_cover_context":{"system":"資料庫"}}',
    )
    assert q_database.startswith("database")
    assert "root cause" in q_database.lower()

    q_storage = _build_retrieval_query(
        section_id="impact",
        context_json='{"manual_cover_context":{"system":"Synology Data Storage"}}',
    )
    assert q_storage.startswith("storage")
    assert "impact" in q_storage.lower()


def test_query_builder_domains_do_not_cross_contaminate() -> None:
    """不同系统域必须解析到不同的检索词，避免跨域召回。"""
    database = _build_retrieval_query(
        section_id="root_cause",
        context_json='{"manual_cover_context":{"system":"MySQL"}}',
    )
    storage = _build_retrieval_query(
        section_id="root_cause",
        context_json='{"manual_cover_context":{"system":"NAS"}}',
    )
    network = _build_retrieval_query(
        section_id="root_cause",
        context_json='{"manual_cover_context":{"system":"Switch"}}',
    )
    assert database.startswith("database")
    assert storage.startswith("storage")
    assert network.startswith("network")
    assert len({database, storage, network}) == 3
