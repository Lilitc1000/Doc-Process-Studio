from typing import Any

from ....chat.application.dtos.attachment import ChatAttachment
from ....chat.router.schemas.request import ChatStreamRequest
from ....common.utils.tool_args import parse_tool_arguments
from ...application.dtos.runtime import SkillConversationState
from ..context import get_skill_context_chunks_by_ids
from ..registry import get_skill_tool_config
from .skill_files import _categorize_relative_path, _normalize_relative_path, _resolve_tool_scope


def _primary_skill_id(request: ChatStreamRequest) -> str:
    if request.selected_skill_ids:
        return request.selected_skill_ids[0]
    return ""


def _build_builtin_status_label(tool_name: str, relative_path: str | None = None) -> str:
    path_category = _categorize_relative_path(relative_path)
    if tool_name == "list_skill_directory":
        if path_category == "reference":
            return "查看参考资料目录"
        if path_category == "script":
            return "查看脚本目录"
        if path_category == "asset":
            return "查看模板资源目录"
        return "查看技能目录"

    if tool_name == "read_skill_file":
        if path_category == "reference":
            return "读取参考资料"
        if path_category == "script":
            return "读取脚本文件"
        if path_category == "asset":
            return "查看模板资源"
        return "读取技能说明"

    if tool_name == "search_skill_context":
        if path_category == "reference":
            return "检索参考资料"
        return "检索技能资料"

    if tool_name == "read_skill_context":
        if path_category == "reference":
            return "载入参考资料"
        return "载入技能上下文"

    return tool_name.replace("_", " ")


def _format_short_path(relative_path: str | None) -> str:
    normalized_path = _normalize_relative_path(relative_path)
    if normalized_path == ".":
        return "根目录"
    return normalized_path


def _get_read_context_relative_path(tool_result: dict[str, Any]) -> str | None:
    raw_chunks = tool_result.get("chunks")
    if not isinstance(raw_chunks, list) or not raw_chunks:
        return None

    first_chunk = raw_chunks[0]
    if not isinstance(first_chunk, dict):
        return None

    source_path = first_chunk.get("source_path")
    if isinstance(source_path, str) and source_path.strip():
        return source_path
    return None


def build_tool_status_start(
    *,
    skill_id: str,
    tool_call: dict[str, Any],
) -> dict[str, str]:
    """根据工具调用上下文生成更业务化的开始状态。"""
    resolved_skill_id, tool_name = _resolve_tool_scope(
        default_skill_id=skill_id,
        tool_call=tool_call,
    )
    arguments = parse_tool_arguments(tool_call)

    if tool_name in {"list_skill_directory", "read_skill_file"}:
        relative_path: str | None = str(arguments.get("relative_path", "")).strip()
        label = _build_builtin_status_label(tool_name, relative_path)
        action = "查看" if tool_name == "list_skill_directory" else "读取"
        return {
            "label": label,
            "message": f"正在{action}{_format_short_path(relative_path)}。",
        }

    if tool_name == "search_skill_context":
        source_path = str(arguments.get("source_path", "")).strip()
        label = _build_builtin_status_label(tool_name, source_path)
        if source_path:
            return {
                "label": label,
                "message": f"正在从 {source_path} 中检索相关内容。",
            }
        return {
            "label": label,
            "message": "正在检索当前技能的相关资料。",
        }

    if tool_name == "read_skill_context":
        raw_chunk_ids = arguments.get("chunk_ids", [])
        chunk_ids = raw_chunk_ids if isinstance(raw_chunk_ids, list) else []
        chunk_count = len(chunk_ids)
        loaded_chunks = (
            get_skill_context_chunks_by_ids(
                skill_id,
                [
                    str(chunk_id).strip()
                    for chunk_id in chunk_ids
                    if isinstance(chunk_id, str) and str(chunk_id).strip()
                ],
            )
            if chunk_ids
            else []
        )
        relative_path = loaded_chunks[0].source_path if loaded_chunks else None
        return {
            "label": _build_builtin_status_label(tool_name, relative_path),
            "message": f"正在载入 {chunk_count or 1} 个技能片段到当前会话上下文。",
        }

    if tool_name == "search_knowledge_base":
        return {
            "label": "检索知识库",
            "message": "正在从知识库中检索相关文档。",
        }

    try:
        declared_tool = get_skill_tool_config(resolved_skill_id, tool_name)
    except ValueError:
        return {
            "label": "执行工具",
            "message": f"正在执行工具：{tool_name or 'unknown'}。",
        }

    if declared_tool.status and declared_tool.status.start:
        return {
            "label": declared_tool.status.label or declared_tool.name,
            "message": declared_tool.status.start,
        }

    return {
        "label": (
            declared_tool.status.label
            if declared_tool.status and declared_tool.status.label
            else declared_tool.description
        ),
        "message": f"正在执行：{declared_tool.description}",
    }


def _build_reused_tool_status(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, str] | None:
    if not tool_result.get("reused"):
        return None

    if tool_name == "list_skill_directory":
        relative_path: str | None = str(arguments.get("relative_path", "")).strip()
        return {
            "label": _build_builtin_status_label(tool_name, relative_path),
            "message": "该目录内容已读取过，本轮不再重复查看。",
        }

    if tool_name == "read_skill_file":
        relative_path = str(arguments.get("relative_path", "")).strip()
        return {
            "label": _build_builtin_status_label(tool_name, relative_path),
            "message": "该文件内容已读取过，本轮不再重复读取。",
        }

    if tool_name == "search_skill_context":
        source_path = str(arguments.get("source_path", "")).strip()
        return {
            "label": _build_builtin_status_label(tool_name, source_path),
            "message": "相同检索条件已执行过，本轮不再重复检索。",
        }

    if tool_name == "read_skill_context":
        relative_path = _get_read_context_relative_path(tool_result)
        return {
            "label": _build_builtin_status_label(tool_name, relative_path),
            "message": "这些技能片段已经在上下文中，本轮不再重复载入。",
        }

    if tool_name == "search_knowledge_base":
        return {
            "label": "检索知识库",
            "message": "相同检索条件已执行过，本轮不再重复检索。",
        }

    return None


def _build_builtin_tool_status(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    tool_result: dict[str, Any],
) -> dict[str, str] | None:
    if tool_name == "list_skill_directory":
        relative_path = str(arguments.get("relative_path", "")).strip()
        return {
            "label": _build_builtin_status_label(tool_name, relative_path),
            "message": f"已列出 {_format_short_path(relative_path)} 的目录内容。",
        }

    if tool_name == "read_skill_file":
        relative_path = str(arguments.get("relative_path", "")).strip()
        return {
            "label": _build_builtin_status_label(tool_name, relative_path),
            "message": f"已读取 {_format_short_path(relative_path)}。",
        }

    if tool_name == "search_skill_context":
        source_path = str(arguments.get("source_path", "")).strip()
        label = _build_builtin_status_label(tool_name, source_path)
        chunks = tool_result.get("chunks")
        result_count = len(chunks) if isinstance(chunks, list) else 0
        if source_path:
            return {
                "label": label,
                "message": f"已从 {source_path} 检索到 {result_count} 条候选片段。",
            }
        return {
            "label": label,
            "message": f"已检索到 {result_count} 条候选技能片段。",
        }

    if tool_name == "read_skill_context":
        read_ctx_path: str | None = _get_read_context_relative_path(tool_result)
        label = _build_builtin_status_label(tool_name, read_ctx_path)
        loaded_chunk_ids = tool_result.get("loaded_chunk_ids")
        chunk_count = len(loaded_chunk_ids) if isinstance(loaded_chunk_ids, list) else 0
        return {
            "label": label,
            "message": f"已将 {chunk_count or 1} 个相关片段加入当前会话上下文。",
        }

    if tool_name == "search_knowledge_base":
        chunks = tool_result.get("chunks")
        result_count = len(chunks) if isinstance(chunks, list) else 0
        return {
            "label": "检索知识库",
            "message": f"已从知识库检索到 {result_count} 条相关文档片段。",
        }

    return None


def _build_declared_tool_status(
    *,
    resolved_skill_id: str,
    tool_name: str,
    tool_result: dict[str, Any],
    attachments: list[ChatAttachment],
) -> dict[str, str]:
    try:
        declared_tool = get_skill_tool_config(resolved_skill_id, tool_name)
    except ValueError:
        error_message = str(tool_result.get("error", "未知错误"))
        return {
            "label": "执行工具",
            "message": f"工具执行失败：{error_message}",
        }

    status_label = (
        declared_tool.status.label if declared_tool.status and declared_tool.status.label else declared_tool.description
    )
    if tool_result.get("reused"):
        return {
            "label": status_label,
            "message": "该工具调用已执行过，本轮不再重复处理，请基于现有结果继续回答。",
        }
    if not tool_result.get("ok"):
        error_message = str(tool_result.get("error", "未知错误"))
        base_message = (
            declared_tool.status.failure if declared_tool.status and declared_tool.status.failure else "工具执行失败。"
        )
        return {
            "label": status_label,
            "message": f"{base_message} {error_message}".strip(),
        }

    if declared_tool.status and declared_tool.status.success:
        return {
            "label": status_label,
            "message": declared_tool.status.success,
        }

    if len(attachments) == 1:
        return {
            "label": status_label,
            "message": f"已生成文件：{attachments[0].name}。",
        }

    if len(attachments) > 1:
        return {
            "label": status_label,
            "message": f"已生成 {len(attachments)} 个文件附件。",
        }

    return {
        "label": status_label,
        "message": "工具执行完成。",
    }


def build_tool_status_finish(
    *,
    request: ChatStreamRequest,
    state: SkillConversationState,
    tool_call: dict[str, Any],
    tool_result: dict[str, Any],
    attachments: list[ChatAttachment],
) -> dict[str, str]:
    del state
    resolved_skill_id, tool_name = _resolve_tool_scope(
        default_skill_id=_primary_skill_id(request),
        tool_call=tool_call,
    )
    arguments = parse_tool_arguments(tool_call)

    reused_status = _build_reused_tool_status(
        tool_name=tool_name,
        arguments=arguments,
        tool_result=tool_result,
    )
    if reused_status is not None:
        return reused_status

    builtin_status = _build_builtin_tool_status(
        tool_name=tool_name,
        arguments=arguments,
        tool_result=tool_result,
    )
    if builtin_status is not None:
        return builtin_status

    return _build_declared_tool_status(
        resolved_skill_id=resolved_skill_id,
        tool_name=tool_name,
        tool_result=tool_result,
        attachments=attachments,
    )
