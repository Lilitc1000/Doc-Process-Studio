import json

from ...models.skill.runtime import (
    SkillContextChunk,
    SkillContextChunkSummary,
    SkillContextPlannerDecision,
    SkillConversationState,
)
from ..infra.ollama_client import extract_first_message_content, post_chat_completion
from .context import search_skill_context_chunks


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


async def request_skill_planner_decision(
    *,
    model: str,
    latest_user_message: str,
    state: SkillConversationState,
    loaded_chunks: list[SkillContextChunk],
    chunk_summaries: list[SkillContextChunkSummary],
) -> SkillContextPlannerDecision:
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

    response_payload = await post_chat_completion(
        model=model,
        messages=[
            {"role": "system", "content": planner_system_prompt},
            {"role": "user", "content": planner_user_prompt},
        ],
    )

    content = extract_first_message_content(response_payload)
    if not content:
        return SkillContextPlannerDecision()

    try:
        return SkillContextPlannerDecision.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValueError):
        return SkillContextPlannerDecision()


def fallback_planner_decision(
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

