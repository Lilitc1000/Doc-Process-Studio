import json
from typing import Any

import httpx

from ..models.chat import ChatMessageInput, ChatStreamRequest
from ..models.skill_runtime import (
    SkillContextChunk,
    SkillContextChunkSummary,
    SkillContextPlannerDecision,
    SkillConversationState,
)
from ..settings import settings
from .skill_context import (
    get_skill_context_chunks_by_ids,
    list_skill_context_chunk_summaries,
    search_skill_context_chunks,
)
from .skill_conversation_store import (
    load_conversation_state,
    save_conversation_state,
)
from .skill_registry import get_skill_interface


def _format_chunk_catalog(
    chunk_summaries: list[SkillContextChunkSummary],
) -> str:
    sections: list[str] = []
    for chunk in chunk_summaries:
        sections.append(
            "\n".join(
                [
                    f"- chunk_id: {chunk.id}",
                    f"  来源: {chunk.source_path}",
                    f"  标题: {chunk.title}",
                    f"  预览: {chunk.preview}",
                ]
            )
        )
    return "\n".join(sections)


def _format_loaded_chunks(chunks: list[SkillContextChunk]) -> str:
    sections: list[str] = []
    for chunk in chunks:
        sections.append(
            "\n".join(
                [
                    f"[chunk_id] {chunk.id}",
                    f"[来源] {chunk.source_path}",
                    f"[标题] {chunk.title}",
                    chunk.content,
                ]
            )
        )
    return "\n\n---\n\n".join(sections)


def _build_local_compact_summary(chunks: list[SkillContextChunk]) -> str:
    if not chunks:
        return ""

    lines: list[str] = ["以下是已压缩保留的 skill 要点："]
    for chunk in chunks:
        snippet = chunk.content.replace("\n", " ").strip()[:140]
        lines.append(
            f"- [{chunk.source_path}] {chunk.title}：{snippet}"
        )

    summary = "\n".join(lines)
    return summary[: settings.skill_compact_summary_max_characters]


async def _request_compact_summary(
    *,
    model: str,
    state: SkillConversationState,
    chunks_to_compact: list[SkillContextChunk],
) -> str:
    if not settings.ollama_base_url or not chunks_to_compact:
        return _build_local_compact_summary(chunks_to_compact)

    summary_system_prompt = (
        "你是 skill 上下文压缩器。"
        "请把给定的 skill 正文片段压缩成高信息密度的长期记忆摘要。"
        "保留角色定位、规则、限制、工作方式、关键模板和重要约束。"
        "输出简洁中文要点，不要编造。"
    )
    summary_user_prompt = "\n\n---\n\n".join(
        [
            "\n".join(
                [
                    f"来源：{chunk.source_path}",
                    f"标题：{chunk.title}",
                    "内容：",
                    chunk.content,
                ]
            )
            for chunk in chunks_to_compact
        ]
    )

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            ChatMessageInput(
                role="system",
                content=summary_system_prompt,
            ).model_dump(),
            ChatMessageInput(
                role="user",
                content=summary_user_prompt,
            ).model_dump(),
        ],
    }

    timeout = httpx.Timeout(
        connect=settings.ollama_timeout_seconds,
        read=settings.ollama_timeout_seconds,
        write=settings.ollama_timeout_seconds,
        pool=settings.ollama_timeout_seconds,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            response_payload = response.json()
    except httpx.HTTPError:
        return _build_local_compact_summary(chunks_to_compact)

    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return _build_local_compact_summary(chunks_to_compact)

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return _build_local_compact_summary(chunks_to_compact)

    message = first_choice.get("message")
    if not isinstance(message, dict):
        return _build_local_compact_summary(chunks_to_compact)

    content = str(message.get("content", "")).strip()
    if not content:
        return _build_local_compact_summary(chunks_to_compact)

    return content[: settings.skill_compact_summary_max_characters]


async def _ensure_compact_summary(
    *,
    model: str,
    state: SkillConversationState,
    chunks_to_compact: list[SkillContextChunk],
) -> None:
    next_compacted_chunk_ids = [chunk.id for chunk in chunks_to_compact]
    if not next_compacted_chunk_ids:
        state.compact_summary = ""
        state.compacted_chunk_ids = []
        return

    if (
        state.compact_summary.strip()
        and state.compacted_chunk_ids == next_compacted_chunk_ids
    ):
        return

    state.compact_summary = await _request_compact_summary(
        model=model,
        state=state,
        chunks_to_compact=chunks_to_compact,
    )
    state.compacted_chunk_ids = next_compacted_chunk_ids


def _build_skill_context_budget_text(
    state: SkillConversationState,
    loaded_chunks: list[SkillContextChunk],
) -> str | None:
    max_characters = settings.skill_context_max_characters
    sections: list[str] = []
    total_length = 0

    compact_summary = state.compact_summary.strip()
    if compact_summary:
        sections.append("以下是之前保留下来的 skill 摘要记忆：\n" + compact_summary)
        total_length += len(sections[-1])

    compacted_chunk_id_set = set(state.compacted_chunk_ids)
    chunks_for_full_injection = [
        chunk for chunk in loaded_chunks if chunk.id not in compacted_chunk_id_set
    ]

    for chunk in chunks_for_full_injection:
        next_section = "\n".join(
            [
                f"来源：{chunk.source_path}",
                f"标题：{chunk.title}",
                "内容：",
                chunk.content,
            ]
        )
        if sections and total_length + len(next_section) > max_characters:
            break
        sections.append(next_section)
        total_length += len(next_section)

    if not sections:
        return None

    return (
        "以下是当前已经加载到会话内的 skill 正文/参考片段。"
        "请把它们视为当前技能的长期上下文，并优先复用这些内容作答：\n\n"
        + "\n\n---\n\n".join(sections)
    )


async def _request_skill_planner_decision(
    *,
    model: str,
    latest_user_message: str,
    state: SkillConversationState,
    loaded_chunks: list[SkillContextChunk],
    chunk_summaries: list[SkillContextChunkSummary],
) -> SkillContextPlannerDecision:
    if not settings.ollama_base_url:
        return SkillContextPlannerDecision()

    if not chunk_summaries:
        return SkillContextPlannerDecision()

    planner_system_prompt = (
        "你是 skill 上下文调度器。"
        "你的任务不是回答用户，而是判断当前问题是否需要再加载更多本地 skill 正文片段。"
        "你必须只输出 JSON，不要输出 Markdown，不要解释。"
        'JSON 结构为 {"should_load_more": boolean, "chunk_ids": string[], "reason": string}。'
        "如果已有上下文足够，就返回 should_load_more=false。"
        "如果需要更多上下文，只能从给定 chunk_id 里选择最相关的少量片段。"
    )

    loaded_chunk_lines = [
        f"- {chunk.id} | {chunk.source_path} | {chunk.title}"
        for chunk in loaded_chunks
    ]
    planner_user_prompt = "\n\n".join(
        [
            f"当前 skill: {state.skill_id}",
            f"最新用户问题:\n{latest_user_message}",
            "已经加载的 chunks:",
            "\n".join(loaded_chunk_lines) or "无",
            "可供选择的 chunks:",
            _format_chunk_catalog(chunk_summaries),
        ]
    )

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            ChatMessageInput(
                role="system",
                content=planner_system_prompt,
            ).model_dump(),
            ChatMessageInput(
                role="user",
                content=planner_user_prompt,
            ).model_dump(),
        ],
    }

    timeout = httpx.Timeout(
        connect=settings.ollama_timeout_seconds,
        read=settings.ollama_timeout_seconds,
        write=settings.ollama_timeout_seconds,
        pool=settings.ollama_timeout_seconds,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        response_payload = response.json()

    content = ""
    choices = response_payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = str(message.get("content", "")).strip()

    if not content:
        return SkillContextPlannerDecision()

    try:
        return SkillContextPlannerDecision.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValueError):
        return SkillContextPlannerDecision()


def _fallback_planner_decision(
    *,
    latest_user_message: str,
    state: SkillConversationState,
) -> SkillContextPlannerDecision:
    matched_chunks = search_skill_context_chunks(
        state.skill_id,
        latest_user_message,
        exclude_chunk_ids=set(state.loaded_chunk_ids),
    )
    return SkillContextPlannerDecision(
        should_load_more=bool(matched_chunks),
        chunk_ids=[chunk.id for chunk in matched_chunks],
        reason="本地关键词检索兜底",
    )


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
                planner_decision = await _request_skill_planner_decision(
                    model=request.model,
                    latest_user_message=latest_user_message,
                    state=state,
                    loaded_chunks=loaded_chunks,
                    chunk_summaries=available_summaries,
                )
            except httpx.HTTPError:
                planner_decision = SkillContextPlannerDecision()

            if not planner_decision.should_load_more or not planner_decision.chunk_ids:
                planner_decision = _fallback_planner_decision(
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
            if kept_chunks and current_length + len(next_section) > settings.skill_context_max_characters:
                compacted_chunks.append(chunk)
                continue

            kept_chunks.append(chunk)
            current_length += len(next_section)

        if compacted_chunks:
            compacted_chunks.reverse()
            await _ensure_compact_summary(
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
