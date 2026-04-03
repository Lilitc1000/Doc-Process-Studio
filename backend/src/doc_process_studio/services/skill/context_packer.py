import httpx

from ...models.skill.runtime import SkillContextChunk, SkillConversationState
from ...settings import settings
from ..infra.ollama_client import (
    OllamaNotConfiguredError,
    extract_first_message_content,
    post_chat_completion,
)


def _build_local_compact_summary(chunks: list[SkillContextChunk]) -> str:
    """在远端压缩失败时，本地兜底生成一份精简摘要。"""
    if not chunks:
        return ""

    lines: list[str] = ["以下是已压缩保留的 skill 要点："]
    for chunk in chunks:
        snippet = chunk.content.replace("\n", " ").strip()[:140]
        lines.append(f"- [{chunk.source_path}] {chunk.title}：{snippet}")

    summary = "\n".join(lines)
    return summary[: settings.skill_compact_summary_max_characters]


async def _request_compact_summary(
    *,
    model: str,
    chunks_to_compact: list[SkillContextChunk],
) -> str:
    if not chunks_to_compact:
        return ""

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

    try:
        response_payload = await post_chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": summary_system_prompt},
                {"role": "user", "content": summary_user_prompt},
            ],
        )
    except (OllamaNotConfiguredError, ValueError, httpx.HTTPError):
        return _build_local_compact_summary(chunks_to_compact)

    content = extract_first_message_content(response_payload)
    if not content:
        return _build_local_compact_summary(chunks_to_compact)

    return content[: settings.skill_compact_summary_max_characters]


async def ensure_compact_summary(
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

