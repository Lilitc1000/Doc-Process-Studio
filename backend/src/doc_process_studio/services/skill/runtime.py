import httpx

from ...models.conversation.stream import ChatStreamRequest
from ...models.skill.runtime import SkillContextChunk, SkillConversationState
from ...settings import settings
from .context import (
    get_skill_context_chunks_by_ids,
    list_skill_context_chunk_summaries,
)
from .context_packer import (
    _build_skill_context_budget_text,
    ensure_compact_summary,
)
from .context_planner import (
    fallback_planner_decision,
    request_skill_planner_decision,
)
from .conversation_store import (
    load_conversation_state,
    save_conversation_state,
)
from .registry import get_skill_interface


async def ensure_skill_context_for_request(
    request: ChatStreamRequest,
) -> tuple[SkillConversationState, str | None]:
    skill_interface = get_skill_interface(request.skill_id)
    state = await load_conversation_state(request.conversation_id)

    if state is None or state.skill_id != request.skill_id:
        state = SkillConversationState(
            conversation_id=request.conversation_id,
            skill_id=request.skill_id,
            system_prompt=skill_interface.default_prompt,
            loaded_chunk_ids=[],
        )

    latest_user_message = ""
    for message in reversed(request.messages):
        if message.role == "user" and message.content.strip():
            latest_user_message = message.content.strip()
            break

    if latest_user_message:
        for _ in range(settings.skill_tool_max_iterations):
            loaded_chunks = get_skill_context_chunks_by_ids(
                state.skill_id,
                state.loaded_chunk_ids,
            )
            available_summaries = [
                summary
                for summary in list_skill_context_chunk_summaries(state.skill_id)
                if summary.id not in set(state.loaded_chunk_ids)
            ]
            if not available_summaries:
                break

            try:
                planner_decision = await request_skill_planner_decision(
                    model=request.model,
                    latest_user_message=latest_user_message,
                    state=state,
                    loaded_chunks=loaded_chunks,
                    chunk_summaries=available_summaries,
                )
            except httpx.HTTPError:
                planner_decision = fallback_planner_decision(
                    latest_user_message=latest_user_message,
                    state=state,
                )

            if not planner_decision.should_load_more or not planner_decision.chunk_ids:
                planner_decision = fallback_planner_decision(
                    latest_user_message=latest_user_message,
                    state=state,
                )

            next_chunk_ids = [
                chunk_id
                for chunk_id in planner_decision.chunk_ids
                if chunk_id not in state.loaded_chunk_ids
            ]
            if not next_chunk_ids:
                break

            state.loaded_chunk_ids.extend(next_chunk_ids)

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
            if (
                kept_chunks
                and current_length + len(next_section)
                > settings.skill_context_max_characters
            ):
                compacted_chunks.append(chunk)
                continue

            kept_chunks.append(chunk)
            current_length += len(next_section)

        if compacted_chunks:
            compacted_chunks.reverse()
            await ensure_compact_summary(
                model=request.model,
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
    return state, _build_skill_context_budget_text(state, loaded_chunks)
