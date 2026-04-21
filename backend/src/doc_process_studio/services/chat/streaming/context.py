from typing import Any

from ....models.conversation.stream import ChatMessageInput, ChatStreamRequest
from ...skill.registry import (
    SKILLS_DIR,
    get_skill_interface,
    list_skill_interfaces,
)


def build_skill_prompt(skill_id: str) -> str:
    return get_skill_interface(skill_id).default_prompt


def _build_skills_catalog_lines(active_skill_ids: list[str]) -> list[str]:
    interfaces = {
        skill.id: skill
        for skill in list_skill_interfaces()
        if skill.id in set(active_skill_ids)
    }
    lines: list[str] = []
    for skill_id in active_skill_ids:
        skill = interfaces.get(skill_id)
        if skill is None:
            continue
        skill_path = (SKILLS_DIR / skill_id / "SKILL.md").as_posix()
        lines.append(
            f"- {skill.id}: {skill.short_description or '无描述'} (file: {skill_path})"
        )
    return lines


def build_multi_skill_runtime_instructions(
    *,
    active_skill_ids: list[str],
    explicit_skill_ids: list[str],
    implicit_skill_ids: list[str] | None = None,
    missing_skill_ids: list[str] | None = None,
) -> str:
    catalog_lines = _build_skills_catalog_lines(active_skill_ids)
    missing_lines = (
        [
            "缺失/受阻：以下文档处理方式当前不可用，请简要说明后继续执行最佳备选方案："
        ]
        + [f"- {skill_id}" for skill_id in missing_skill_ids]
        if missing_skill_ids
        else []
    )
    explicit_line = (
        "本轮用户显式选择了以下文档处理方式，必须优先使用："
        + ", ".join(explicit_skill_ids)
        if explicit_skill_ids
        else "本轮用户未显式选择文档处理方式，你可以根据任务描述从可用方式中选择最小集合隐式调用。"
    )
    implicit_line = (
        "规划层根据本轮用户输入追加了以下隐式文档处理方式："
        + ", ".join(implicit_skill_ids or [])
        if implicit_skill_ids
        else "规划层未追加隐式文档处理方式。"
    )

    return "\n".join(
        [
            "你当前正在使用本地文档处理方式（skills）系统。",
            "发现：以下是本轮可用文档处理方式（名称、描述、SKILL.md 路径）：",
            *catalog_lines,
            explicit_line,
            implicit_line,
            "系统级文档处理方式 document-assistant 始终启用，优先级最高。",
            "回复语言策略：默认与用户最近一轮输入语言保持一致；若用户明确要求输出语言，优先遵从用户要求。",
            "触发规则：若用户通过输入框显式选择，或在消息中使用 $SkillName 明确提及某方式，当前轮必须使用；若提及多个，必须全部使用；除非再次提及，不跨轮沿用。",
            "未显式选择时，可根据任务描述按最小集合隐式调用；隐式调用由规划层建议，可按实际任务取舍。",
            "技能使用方法（渐进式披露）：先读 SKILL.md 必要部分；若引用 references/，仅按需读取必要文件；优先复用 scripts/ 与 assets/。",
            "上下文管理：只摘要必要内容，不要全文粘贴；非阻塞时不要深挖多级引用链。",
            "安全与回退：若某方式文件缺失或不可读，明确说明问题并切换到次优方案继续完成任务。",
            *missing_lines,
        ]
    )


def build_upstream_messages_for_skills(
    *,
    request: ChatStreamRequest,
    active_skill_ids: list[str],
    explicit_skill_ids: list[str],
    implicit_skill_ids: list[str] | None = None,
    skill_context_by_skill: dict[str, str] | None = None,
    uploaded_files_context: str | None = None,
    extra_messages: list[dict[str, Any]] | None = None,
    missing_skill_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    primary_skill_id = (
        active_skill_ids[0]
        if active_skill_ids
        else "document-assistant"
    )
    primary_prompt = build_skill_prompt(primary_skill_id)
    system_message = ChatMessageInput(role="system", content=primary_prompt)
    upstream_messages: list[dict[str, Any]] = [system_message.model_dump()]
    upstream_messages.append(
        ChatMessageInput(
            role="system",
            content=build_multi_skill_runtime_instructions(
                active_skill_ids=active_skill_ids,
                explicit_skill_ids=explicit_skill_ids,
                implicit_skill_ids=implicit_skill_ids or [],
                missing_skill_ids=missing_skill_ids or [],
            ),
        ).model_dump()
    )

    if skill_context_by_skill:
        for skill_id in active_skill_ids:
            skill_context = skill_context_by_skill.get(skill_id, "").strip()
            if not skill_context:
                continue
            upstream_messages.append(
                ChatMessageInput(
                    role="system",
                    content=f"[{skill_id}] 上下文：\n{skill_context}",
                ).model_dump()
            )

    if uploaded_files_context:
        upstream_messages.append(
            ChatMessageInput(
                role="user",
                content=uploaded_files_context,
            ).model_dump()
        )

    upstream_messages.extend([message.model_dump() for message in request.messages])
    if extra_messages:
        upstream_messages.extend(extra_messages)
    return upstream_messages


def format_output_name_from_template(
    template: str | None,
    payload: dict[str, Any],
) -> str | None:
    if not template:
        return None

    format_payload = {
        key: value
        for key, value in payload.items()
        if isinstance(value, (str, int, float))
    }
    try:
        rendered_name = template.format(**format_payload).strip()
    except Exception:
        return None
    return rendered_name or None


def merge_uploaded_files_context(
    *contexts: str | None,
) -> str | None:
    normalized_sections = [
        context.strip() for context in contexts if isinstance(context, str) and context.strip()
    ]
    if not normalized_sections:
        return None
    return "\n\n".join(normalized_sections)
