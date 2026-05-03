import logging

import httpx

from ..schemas.runtime import SkillContextChunk, SkillConversationState
from ...core.config import settings
from ...core.ollama import (
    OllamaNotConfiguredError,
    extract_first_message_content,
    post_chat_completion,
)

logger = logging.getLogger(__name__)


def _build_local_summary_from_chunks(
    *,
    chunks: list[SkillContextChunk],
    title: str,
    max_characters: int,
) -> str:
    if not chunks:
        return ""

    lines: list[str] = [title]
    for chunk in chunks:
        snippet = chunk.content.replace("\n", " ").strip()[:160]
        lines.append(f"- [{chunk.source_path}] {chunk.title}：{snippet}")

    summary = "\n".join(lines)
    return summary[:max_characters]


def _build_local_summary_from_text(
    *,
    text: str,
    title: str,
    max_characters: int,
) -> str:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return ""
    return (title + "\n" + normalized[: max_characters - len(title) - 1]).strip()[:max_characters]


async def _request_summary(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_characters: int,
) -> str:
    if not user_prompt.strip():
        return ""

    try:
        response_payload = await post_chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except (OllamaNotConfiguredError, ValueError, httpx.HTTPError):
        logger.debug("AI 摘要请求失败，返回空字符串")
        return ""

    content = extract_first_message_content(response_payload).strip()
    if not content:
        return ""
    return content[:max_characters]


async def ensure_hierarchical_memory(
    *,
    model: str,
    state: SkillConversationState,
    chunks_to_compact: list[SkillContextChunk],
    force: bool = False,
) -> None:
    next_compacted_chunk_ids = [chunk.id for chunk in chunks_to_compact]
    if not next_compacted_chunk_ids:
        state.short_term_memory = ""
        state.compacted_chunk_ids = []
        return

    if (
        not force
        and state.compacted_chunk_ids == next_compacted_chunk_ids
        and state.short_term_memory.strip()
    ):
        return

    short_term_prompt = "\n\n---\n\n".join(
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
    short_term_memory = await _request_summary(
        model=model,
        system_prompt=(
            "你是短期记忆压缩器。"
            "请把输入片段压缩成短期可复用摘要，突出本轮任务直接相关的信息。"
            "输出简洁中文要点，不要编造。"
        ),
        user_prompt=short_term_prompt,
        max_characters=settings.skill_memory_short_term_max_characters,
    )
    if not short_term_memory:
        short_term_memory = _build_local_summary_from_chunks(
            chunks=chunks_to_compact,
            title="短期记忆要点：",
            max_characters=settings.skill_memory_short_term_max_characters,
        )

    episodic_source = "\n\n".join(
        [value for value in [state.episodic_memory.strip(), short_term_memory.strip()] if value]
    )
    episodic_memory = await _request_summary(
        model=model,
        system_prompt=(
            "你是情节记忆压缩器。"
            "请把历史摘要与新摘要融合为可跨轮复用的情节记忆。"
            "保留关键过程、约束、决策与已完成信息。"
        ),
        user_prompt=episodic_source,
        max_characters=settings.skill_memory_episodic_max_characters,
    )
    if not episodic_memory:
        episodic_memory = _build_local_summary_from_text(
            text=episodic_source,
            title="情节记忆：",
            max_characters=settings.skill_memory_episodic_max_characters,
        )

    long_term_seed = "\n\n".join(
        [
            value
            for value in [
                state.skill_memory.strip(),
                episodic_memory.strip(),
            ]
            if value
        ]
    )
    skill_memory = await _request_summary(
        model=model,
        system_prompt=(
            "你是技能长期记忆压缩器。"
            "请保留稳定且跨轮有效的技能规则、限制、模板与关键背景。"
            "输出应可长期复用，避免写瞬时噪声。"
        ),
        user_prompt=long_term_seed,
        max_characters=settings.skill_memory_long_term_max_characters,
    )
    if not skill_memory:
        skill_memory = _build_local_summary_from_text(
            text=long_term_seed,
            title="技能记忆：",
            max_characters=settings.skill_memory_long_term_max_characters,
        )

    state.short_term_memory = short_term_memory
    state.episodic_memory = episodic_memory
    state.skill_memory = skill_memory
    state.compacted_chunk_ids = next_compacted_chunk_ids


def build_skill_context_budget_text(
    state: SkillConversationState,
    loaded_chunks: list[SkillContextChunk],
) -> str | None:
    max_characters = settings.skill_context_max_characters
    sections: list[str] = []
    total_length = 0

    memory_sections = [
        ("技能记忆（长期）：", state.skill_memory.strip()),
        ("情节记忆（跨轮）：", state.episodic_memory.strip()),
        ("短期记忆（当前任务）：", state.short_term_memory.strip()),
    ]
    for title, content in memory_sections:
        if not content:
            continue
        section = f"{title}\n{content}"
        if sections and total_length + len(section) > max_characters:
            break
        sections.append(section)
        total_length += len(section)

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
        "以下是当前已经加载到会话内的技能上下文（含层级记忆与正文片段）。"
        "请优先复用这些信息作答：\n\n"
        + "\n\n---\n\n".join(sections)
    )

