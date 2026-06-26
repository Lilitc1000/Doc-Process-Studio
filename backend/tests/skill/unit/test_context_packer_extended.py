from unittest.mock import patch

from doc_process_studio.skill.application.dtos.runtime import SkillContextChunk, SkillConversationState
from doc_process_studio.skill.infrastructure.context_packer import (
    _build_local_summary_from_chunks,
    _build_local_summary_from_text,
    _request_summary,
    build_skill_context_budget_text,
    ensure_hierarchical_memory,
)


def _make_chunk(**overrides) -> SkillContextChunk:
    defaults = dict(
        id="chunk-1",
        skill_id="test-skill",
        source_path="references/doc.md",
        title="测试文档",
        preview="预览内容",
        content="这是测试内容，用于验证摘要生成逻辑。",
    )
    defaults.update(overrides)
    return SkillContextChunk(**defaults)


def _make_state(**overrides) -> SkillConversationState:
    defaults = dict(
        conversation_id="conv-1",
        skill_id="test-skill",
        system_prompt="系统提示词",
        short_term_memory="",
        episodic_memory="",
        skill_memory="",
        compacted_chunk_ids=[],
    )
    defaults.update(overrides)
    return SkillConversationState(**defaults)


def test_build_local_summary_from_chunks_empty():
    result = _build_local_summary_from_chunks(chunks=[], title="标题", max_characters=500)
    assert result == ""


def test_build_local_summary_from_chunks_basic():
    chunks = [_make_chunk()]
    result = _build_local_summary_from_chunks(chunks=chunks, title="摘要：", max_characters=500)
    assert "摘要：" in result
    assert "doc.md" in result
    assert "测试文档" in result


def test_build_local_summary_from_chunks_truncation():
    chunks = [_make_chunk(content="x" * 200)]
    result = _build_local_summary_from_chunks(chunks=chunks, title="标题：", max_characters=50)
    assert len(result) <= 50


def test_build_local_summary_from_chunks_multiple():
    chunks = [
        _make_chunk(id="c1", source_path="a.md", title="A", content="内容A"),
        _make_chunk(id="c2", source_path="b.md", title="B", content="内容B"),
    ]
    result = _build_local_summary_from_chunks(chunks=chunks, title="摘要：", max_characters=500)
    assert "a.md" in result
    assert "b.md" in result


def test_build_local_summary_from_text_empty():
    result = _build_local_summary_from_text(text="", title="标题：", max_characters=500)
    assert result == ""


def test_build_local_summary_from_text_whitespace_only():
    result = _build_local_summary_from_text(text="   \n\t  ", title="标题：", max_characters=500)
    assert result == ""


def test_build_local_summary_from_text_basic():
    result = _build_local_summary_from_text(text="这是测试文本内容", title="摘要：", max_characters=500)
    assert "摘要：" in result
    assert "测试文本" in result


def test_build_local_summary_from_text_truncation():
    result = _build_local_summary_from_text(text="x" * 200, title="标题：", max_characters=50)
    assert len(result) <= 50


async def test_request_summary_empty_prompt():
    result = await _request_summary(model="test", system_prompt="sys", user_prompt="", max_characters=500)
    assert result == ""


async def test_request_summary_whitespace_prompt():
    result = await _request_summary(model="test", system_prompt="sys", user_prompt="   ", max_characters=500)
    assert result == ""


async def test_request_summary_llm_error():
    with patch(
        "doc_process_studio.skill.infrastructure.context_packer.post_chat_completion",
        side_effect=ValueError("LLM error"),
    ):
        result = await _request_summary(model="test", system_prompt="sys", user_prompt="test", max_characters=500)
    assert result == ""


async def test_request_summary_ollama_not_configured():
    from doc_process_studio.common.infrastructure.exceptions import OllamaNotConfiguredError

    with patch(
        "doc_process_studio.skill.infrastructure.context_packer.post_chat_completion",
        side_effect=OllamaNotConfiguredError("not configured"),
    ):
        result = await _request_summary(model="test", system_prompt="sys", user_prompt="test", max_characters=500)
    assert result == ""


async def test_request_summary_http_error():
    import httpx

    with patch(
        "doc_process_studio.skill.infrastructure.context_packer.post_chat_completion",
        side_effect=httpx.HTTPError("connection error"),
    ):
        result = await _request_summary(model="test", system_prompt="sys", user_prompt="test", max_characters=500)
    assert result == ""


async def test_request_summary_empty_content():
    with (
        patch(
            "doc_process_studio.skill.infrastructure.context_packer.post_chat_completion",
            return_value={"choices": [{"message": {"content": "  "}}]},
        ),
        patch(
            "doc_process_studio.skill.infrastructure.context_packer.extract_first_message_content",
            return_value="  ",
        ),
    ):
        result = await _request_summary(model="test", system_prompt="sys", user_prompt="test", max_characters=500)
    assert result == ""


async def test_ensure_hierarchical_memory_empty_chunks():
    state = _make_state()
    await ensure_hierarchical_memory(model="test", state=state, chunks_to_compact=[])
    assert state.short_term_memory == ""
    assert state.compacted_chunk_ids == []


async def test_ensure_hierarchical_memory_same_chunks_cached():
    state = _make_state(short_term_memory="已有摘要", compacted_chunk_ids=["chunk-1"])
    chunks = [_make_chunk()]
    await ensure_hierarchical_memory(model="test", state=state, chunks_to_compact=chunks, force=False)
    assert state.short_term_memory == "已有摘要"


async def test_ensure_hierarchical_memory_force_refresh():
    state = _make_state(short_term_memory="旧摘要", compacted_chunk_ids=["chunk-1"])
    chunks = [_make_chunk()]

    with patch(
        "doc_process_studio.skill.infrastructure.context_packer._request_summary",
        return_value="新摘要",
    ):
        await ensure_hierarchical_memory(model="test", state=state, chunks_to_compact=chunks, force=True)
    assert state.short_term_memory == "新摘要"


async def test_ensure_hierarchical_memory_fallback_to_local():
    state = _make_state()
    chunks = [_make_chunk()]

    with patch(
        "doc_process_studio.skill.infrastructure.context_packer._request_summary",
        return_value="",
    ):
        await ensure_hierarchical_memory(model="test", state=state, chunks_to_compact=chunks, force=True)
    assert "测试文档" in state.short_term_memory or len(state.short_term_memory) > 0


def test_build_skill_context_budget_text_empty():
    state = _make_state()
    result = build_skill_context_budget_text(state, [])
    assert result is None


def test_build_skill_context_budget_text_with_memory():
    state = _make_state(skill_memory="长期记忆内容", episodic_memory="情节记忆内容", short_term_memory="短期记忆内容")
    result = build_skill_context_budget_text(state, [])
    assert result is not None
    assert "长期记忆" in result
    assert "情节记忆" in result
    assert "短期记忆" in result


def test_build_skill_context_budget_text_with_chunks():
    state = _make_state()
    chunks = [_make_chunk()]
    result = build_skill_context_budget_text(state, chunks)
    assert result is not None
    assert "doc.md" in result


def test_build_skill_context_budget_text_compacted_chunks_excluded():
    state = _make_state(compacted_chunk_ids=["chunk-1"])
    chunks = [_make_chunk()]
    result = build_skill_context_budget_text(state, chunks)
    assert result is None


def test_build_skill_context_budget_text_mixed():
    state = _make_state(short_term_memory="短期记忆", compacted_chunk_ids=["chunk-1"])
    chunks = [
        _make_chunk(),
        _make_chunk(id="chunk-2", source_path="refs/other.md", title="其他文档", content="其他内容"),
    ]
    result = build_skill_context_budget_text(state, chunks)
    assert result is not None
    assert "短期记忆" in result
    assert "other.md" in result
