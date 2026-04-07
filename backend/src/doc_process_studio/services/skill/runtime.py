from ...models.conversation.stream import ChatStreamRequest
from ...models.skill.runtime import SkillContextChunk, SkillConversationState
from ...settings import settings
from .context import get_skill_context_chunks_by_ids
from .context_packer import (
    build_skill_context_budget_text,
    ensure_compact_summary,
)
from .conversation_store import (
    load_conversation_state,
    save_conversation_state,
)
from .registry import get_skill_interface


async def sync_skill_context_state(
    *,
    model: str,
    state: SkillConversationState,
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
            settings.skill_compact_summary_max_characters,
            max(len(state.compact_summary.strip()), 320),
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
            if kept_chunks and current_length + len(next_section) > settings.skill_context_max_characters:
                compacted_chunks.append(chunk)
                continue

            kept_chunks.append(chunk)
            current_length += len(next_section)

        if compacted_chunks:
            compacted_chunks.reverse()
            await ensure_compact_summary(
                model=model,
                state=state,
                chunks_to_compact=compacted_chunks,
            )
        elif state.compact_summary or state.compacted_chunk_ids:
            state.compact_summary = ""
            state.compacted_chunk_ids = []

    await save_conversation_state(state)
    loaded_chunks = get_skill_context_chunks_by_ids(
        state.skill_id,
        state.loaded_chunk_ids,
    )
    return build_skill_context_budget_text(state, loaded_chunks)


async def ensure_skill_context_for_request(
    request: ChatStreamRequest,
) -> tuple[SkillConversationState, str | None]:
    """读取或初始化当前会话的 skill 状态，并返回已有上下文。"""
    skill_interface = get_skill_interface(request.skill_id)
    state = await load_conversation_state(request.conversation_id)

    if state is None or state.skill_id != request.skill_id:
        state = SkillConversationState(
            conversation_id=request.conversation_id,
            skill_id=request.skill_id,
            system_prompt=skill_interface.default_prompt,
            loaded_chunk_ids=[],
        )

    return state, await sync_skill_context_state(model=request.model, state=state)
