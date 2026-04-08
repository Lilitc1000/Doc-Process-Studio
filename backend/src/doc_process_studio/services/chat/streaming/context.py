from typing import Any

from ....models.conversation.stream import ChatMessageInput, ChatStreamRequest
from ...skill.registry import get_skill_interface


def build_skill_prompt(skill_id: str) -> str:
    return get_skill_interface(skill_id).default_prompt


def build_skill_runtime_instructions(skill_id: str) -> str:
    skill_interface = get_skill_interface(skill_id)
    declared_tool_names = (
        ", ".join(tool.name for tool in skill_interface.tools) or "无声明式工具"
    )

    return "\n".join(
        [
            "你当前正在使用一个本地 skill。",
            f"当前 skill_id: {skill_interface.id}",
            f"当前 skill 名称: {skill_interface.display_name}",
            f"skill 简介: {skill_interface.short_description or '无'}",
            f"已声明工具: {declared_tool_names}",
            "请遵循渐进式披露：先查看技能目录，再优先读取 SKILL.md；若 SKILL.md 引用了 references、scripts 或 assets，再按需继续读取。",
            "不要一次性读取整个 skill 目录。",
            "如果 skill 中已经声明了可执行工具，应优先调用这些声明式工具，而不是在回答里手写脚本让用户自己运行。",
            "若工具已返回附件，请直接说明可从附件下载，不要输出 file:// 或 /tmp 等本地临时路径。",
        ]
    )


def build_upstream_messages(
    request: ChatStreamRequest,
    skill_context: str | None = None,
    uploaded_files_context: str | None = None,
    extra_messages: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    system_message = ChatMessageInput(
        role="system",
        content=build_skill_prompt(request.skill_id),
    )
    upstream_messages: list[dict[str, Any]] = [system_message.model_dump()]
    upstream_messages.append(
        ChatMessageInput(
            role="system",
            content=build_skill_runtime_instructions(request.skill_id),
        ).model_dump()
    )
    if skill_context:
        upstream_messages.append(
            ChatMessageInput(
                role="system",
                content=skill_context,
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

