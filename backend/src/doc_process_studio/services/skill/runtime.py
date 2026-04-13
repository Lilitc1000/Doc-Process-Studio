from ...models.skill.runtime import SkillContextChunk, SkillConversationState
from ...settings import settings
from .context import get_skill_context_chunks_by_ids
from .context_packer import (
    build_skill_context_budget_text,
    ensure_hierarchical_memory,
)


async def sync_skill_context_state(
    *,
    model: str,
    state: SkillConversationState,
    force_compact: bool = False,
) -> str | None:
    """根据当前已加载 chunk 同步压缩摘要，并返回可注入的 skill 上下文。"""
    loaded_chunks = get_skill_context_chunks_by_ids(
        state.skill_id,
        state.loaded_chunk_ids,
    )
    if loaded_chunks:
        kept_chunks: list[SkillContextChunk] = []
        compacted_chunks: list[SkillContextChunk] = []
        projected_summary_length = min(
            settings.skill_memory_long_term_max_characters,
            max(len(state.skill_memory.strip()), 320),
        )
        current_length = projected_summary_length if len(loaded_chunks) > 1 else 0

        for chunk in reversed(loaded_chunks):
            next_section = "\n".join(
                [
                    f"来源：{chunk.source_path}",
                    f"标题：{chunk.title}",
                    "内容：",
                    chunk.content,
                ]
            )
            if force_compact and len(kept_chunks) >= 1:
                compacted_chunks.append(chunk)
                continue
            if (
                kept_chunks
                and current_length + len(next_section) > settings.skill_context_max_characters
            ):
                compacted_chunks.append(chunk)
                continue

            kept_chunks.append(chunk)
            current_length += len(next_section)

        if compacted_chunks:
            compacted_chunks.reverse()
            await ensure_hierarchical_memory(
                model=model,
                state=state,
                chunks_to_compact=compacted_chunks,
                force=force_compact,
            )
        elif state.short_term_memory or state.compacted_chunk_ids:
            state.short_term_memory = ""
            state.compacted_chunk_ids = []

    loaded_chunks = get_skill_context_chunks_by_ids(
        state.skill_id,
        state.loaded_chunk_ids,
    )
    return build_skill_context_budget_text(state, loaded_chunks)
