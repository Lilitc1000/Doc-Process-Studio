import doc_process_studio.skill.service.runtime as runtime_module
from doc_process_studio.skill.schemas.runtime import SkillContextChunk, SkillConversationState


def _make_chunk(chunk_id="c1", content="chunk content", title="Test", source_path="ref.md"):
    return SkillContextChunk(
        id=chunk_id, skill_id="test-skill", source_path=source_path,
        title=title, preview=content[:80], content=content,
    )


async def test_sync_skill_context_state_no_chunks(monkeypatch):
    monkeypatch.setattr(runtime_module, "get_skill_context_chunks_by_ids", lambda sid, cids: [])
    state = SkillConversationState(conversation_id="conv-1", skill_id="test-skill", system_prompt="test")
    result = await runtime_module.sync_skill_context_state(model="test", state=state)
    assert result is None


async def test_sync_skill_context_state_with_chunks(monkeypatch):
    chunks = [_make_chunk(chunk_id="c1", content="a" * 100)]
    call_count = 0

    def _fake_get_chunks(sid, cids):
        nonlocal call_count
        call_count += 1
        return chunks

    monkeypatch.setattr(runtime_module, "get_skill_context_chunks_by_ids", _fake_get_chunks)

    async def _fake_ensure(*, model, state, chunks_to_compact, force=False):
        state.short_term_memory = "compressed"
        state.compacted_chunk_ids = [c.id for c in chunks_to_compact]

    monkeypatch.setattr(runtime_module, "ensure_hierarchical_memory", _fake_ensure)

    monkeypatch.setattr(runtime_module, "build_skill_context_budget_text", lambda s, c: "context text")

    state = SkillConversationState(
        conversation_id="conv-1", skill_id="test-skill", system_prompt="test",
        loaded_chunk_ids=["c1"],
    )
    result = await runtime_module.sync_skill_context_state(model="test", state=state, force_compact=True)
    assert result is not None


async def test_sync_skill_context_state_clears_stale_memory(monkeypatch):
    chunk = _make_chunk(chunk_id="c1", content="short")
    monkeypatch.setattr(
        runtime_module,
        "get_skill_context_chunks_by_ids",
        lambda sid, cids: [chunk] if "c1" in cids else [],
    )
    monkeypatch.setattr(
        runtime_module,
        "build_skill_context_budget_text",
        lambda s, c: "context",
    )
    state = SkillConversationState(
        conversation_id="conv-1",
        skill_id="test-skill",
        system_prompt="test",
        loaded_chunk_ids=["c1"],
        short_term_memory="stale",
        compacted_chunk_ids=["old"],
    )
    await runtime_module.sync_skill_context_state(model="test", state=state)
    assert state.short_term_memory == ""
    assert state.compacted_chunk_ids == []
