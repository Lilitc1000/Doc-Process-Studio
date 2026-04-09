import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

from ...models.conversation.attachments import ChatAttachment
from ...models.conversation.stream import ChatStreamRequest
from ...models.skill.catalog import SkillToolConfig
from ...models.skill.runtime import SkillConversationState
from ...settings import BACKEND_DIR, settings
from ..chat.attachments import save_generated_attachment
from .context import (
    get_skill_context_chunks_by_ids,
    search_skill_context_chunks,
)
from .registry import (
    SKILLS_DIR,
    get_skill_interface,
    get_skill_interaction_config,
    get_skill_tool_config,
)

TEXT_FILE_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".html",
    ".htm",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".psm1",
    ".sql",
    ".csv",
}

DEFAULT_STRUCTURED_TEXT_TITLE = "文档内容"
SCOPED_TOOL_SEPARATOR = "::"


def compose_scoped_tool_name(skill_id: str, tool_name: str) -> str:
    return f"{skill_id}{SCOPED_TOOL_SEPARATOR}{tool_name}"


def split_scoped_tool_name(tool_name: str) -> tuple[str | None, str]:
    normalized_name = tool_name.strip()
    if SCOPED_TOOL_SEPARATOR not in normalized_name:
        return None, normalized_name
    skill_id, base_tool_name = normalized_name.split(SCOPED_TOOL_SEPARATOR, 1)
    return skill_id.strip() or None, base_tool_name.strip()


def _get_skill_root(skill_id: str) -> Path:
    return (SKILLS_DIR / skill_id).resolve()


def _resolve_skill_relative_path(skill_id: str, relative_path: str) -> Path:
    skill_root = _get_skill_root(skill_id)
    candidate_path = (skill_root / relative_path).resolve()
    try:
        candidate_path.relative_to(skill_root)
    except ValueError as exc:
        raise ValueError(f"不允许访问 skill 目录外的路径：{relative_path}") from exc
    return candidate_path


def _list_directory_entries(skill_id: str, relative_path: str = "") -> list[dict[str, str]]:
    target_dir = _resolve_skill_relative_path(skill_id, relative_path or ".")
    if not target_dir.is_dir():
        raise ValueError(f"目录不存在：{relative_path or '.'}")

    skill_root = _get_skill_root(skill_id)
    entries: list[dict[str, str]] = []
    for entry in sorted(target_dir.iterdir(), key=lambda item: (not item.is_dir(), item.name)):
        entry_type = "directory" if entry.is_dir() else "file"
        entries.append(
            {
                "name": entry.name,
                "path": entry.relative_to(skill_root).as_posix(),
                "type": entry_type,
            }
        )
    return entries


def _read_text_file(path: Path) -> str | None:
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return None


def _read_skill_file_content(skill_id: str, relative_path: str) -> dict[str, Any]:
    target_path = _resolve_skill_relative_path(skill_id, relative_path)
    if not target_path.is_file():
        raise ValueError(f"文件不存在：{relative_path}")

    skill_root = _get_skill_root(skill_id)
    suffix = target_path.suffix.lower()
    if suffix not in TEXT_FILE_EXTENSIONS:
        return {
            "path": target_path.relative_to(skill_root).as_posix(),
            "kind": "binary",
            "message": "该文件为二进制或非文本文件，不直接返回正文内容。",
        }

    file_content = _read_text_file(target_path)
    if file_content is None:
        return {
            "path": target_path.relative_to(skill_root).as_posix(),
            "kind": "text",
            "message": "文件存在，但当前无法按文本安全读取。",
        }

    truncated_content = file_content[: settings.skill_context_max_characters]
    if len(file_content) > len(truncated_content):
        truncated_content += "\n\n[文件内容过长，已截断展示]"

    return {
        "path": target_path.relative_to(skill_root).as_posix(),
        "kind": "text",
        "content": truncated_content,
}


def _normalize_relative_path(relative_path: str | None) -> str:
    normalized_path = (relative_path or "").strip().replace("\\", "/")
    if normalized_path in {"", "."}:
        return "."
    return normalized_path


def _categorize_relative_path(relative_path: str | None) -> str:
    normalized_path = _normalize_relative_path(relative_path)
    if normalized_path == "." or normalized_path == "SKILL.md":
        return "skill"
    if normalized_path.startswith("references/") or normalized_path == "references":
        return "reference"
    if normalized_path.startswith("scripts/") or normalized_path == "scripts":
        return "script"
    if normalized_path.startswith("assets/") or normalized_path == "assets":
        return "asset"
    return "other"


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
    arguments = _parse_tool_arguments(tool_call)

    if tool_name == "start_skill_interaction":
        return {
            "label": "收集报告信息",
            "message": "正在启动交互向导并准备分步采集。",
        }

    if tool_name in {"list_skill_directory", "read_skill_file"}:
        relative_path = str(arguments.get("relative_path", "")).strip()
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


def build_tool_status_finish(
    *,
    request: ChatStreamRequest,
    state: SkillConversationState,
    tool_call: dict[str, Any],
    tool_result: dict[str, Any],
    attachments: list[ChatAttachment],
) -> dict[str, str]:
    """根据工具执行结果生成更业务化的完成状态。"""
    del state
    resolved_skill_id, tool_name = _resolve_tool_scope(
        default_skill_id=request.skill_id,
        tool_call=tool_call,
    )
    arguments = _parse_tool_arguments(tool_call)
    if tool_name == "start_skill_interaction":
        if tool_result.get("ok"):
            return {
                "label": "收集报告信息",
                "message": "已进入交互向导，等待用户补充信息。",
            }
        error_message = str(tool_result.get("error", "未知错误"))
        return {
            "label": "收集报告信息",
            "message": f"启动交互向导失败：{error_message}",
        }

    if tool_result.get("reused"):
        if tool_name == "list_skill_directory":
            relative_path = str(arguments.get("relative_path", "")).strip()
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
        relative_path = _get_read_context_relative_path(tool_result)
        label = _build_builtin_status_label(tool_name, relative_path)
        loaded_chunk_ids = tool_result.get("loaded_chunk_ids")
        chunk_count = len(loaded_chunk_ids) if isinstance(loaded_chunk_ids, list) else 0
        return {
            "label": label,
            "message": f"已将 {chunk_count or 1} 个相关片段加入当前会话上下文。",
        }

    try:
        declared_tool = get_skill_tool_config(resolved_skill_id, tool_name)
    except ValueError:
        error_message = str(tool_result.get("error", "未知错误"))
        return {
            "label": "执行工具",
            "message": f"工具执行失败：{error_message}",
        }

    status_label = (
        declared_tool.status.label
        if declared_tool.status and declared_tool.status.label
        else declared_tool.description
    )
    if tool_result.get("reused"):
        return {
            "label": status_label,
            "message": "该工具调用已执行过，本轮不再重复处理，请基于现有结果继续回答。",
        }
    if not tool_result.get("ok"):
        error_message = str(tool_result.get("error", "未知错误"))
        base_message = (
            declared_tool.status.failure
            if declared_tool.status and declared_tool.status.failure
            else "工具执行失败。"
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


def build_skill_tools(skill_id: str) -> list[dict[str, Any]]:
    """构造当前 skill 对模型暴露的全部工具。"""
    skill_interface = get_skill_interface(skill_id)
    builtin_tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "list_skill_directory",
                "description": "列出当前 skill 某个目录下的文件和子目录，优先用于发现 SKILL.md、references、scripts、assets。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "相对于 skill 根目录的路径，默认根目录。",
                        }
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_file",
                "description": "读取 skill 内某个具体文本文件的内容，例如 SKILL.md 或 references 下的说明文件。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "相对于 skill 根目录的文件路径。",
                        }
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_skill_context",
                "description": "按问题搜索当前 skill 的相关片段，可选限定到特定 source_path。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "检索关键词或自然语言问题。",
                        },
                        "source_path": {
                            "type": "string",
                            "description": "可选。限定搜索的相对路径，如 references/doc-plan-example.yaml。",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 8,
                            "description": "最多返回多少条结果。",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_context",
                "description": "读取指定 chunk 的正文，并将这些 chunk 加入当前会话长期上下文。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chunk_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 6,
                        }
                    },
                    "required": ["chunk_ids"],
                    "additionalProperties": False,
                },
            },
        },
    ]
    interaction_config = get_skill_interaction_config(skill_id)
    if interaction_config is not None:
        builtin_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "start_skill_interaction",
                    "description": (
                        "当用户目标是生成文档但当前信息不足时，启动或恢复该技能的分步交互向导。"
                        "若信息已经完整则不要调用。"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "可选。简述为何需要向导补充信息。",
                            }
                        },
                        "additionalProperties": False,
                    },
                },
            }
        )

    declared_tools: list[dict[str, Any]] = []
    for tool in skill_interface.tools:
        declared_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
        )

    return [*builtin_tools, *declared_tools]


def build_skill_tools_for_skills(skill_ids: list[str]) -> list[dict[str, Any]]:
    """构造多 skill 联合工具集：内置检索工具共享，声明式工具按 skill 名称空间隔离。"""
    normalized_skill_ids: list[str] = []
    for skill_id in skill_ids:
        normalized_skill_id = skill_id.strip()
        if normalized_skill_id and normalized_skill_id not in normalized_skill_ids:
            normalized_skill_ids.append(normalized_skill_id)

    if not normalized_skill_ids:
        return []

    builtin_tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "list_skill_directory",
                "description": "列出指定文档处理方式(skill)目录下的文件和子目录。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "目标文档处理方式标识；不传时默认当前主处理方式。",
                        },
                        "relative_path": {
                            "type": "string",
                            "description": "相对于 skill 根目录的路径，默认根目录。",
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_file",
                "description": "读取指定文档处理方式(skill)内某个具体文本文件内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "目标文档处理方式标识；不传时默认当前主处理方式。",
                        },
                        "relative_path": {
                            "type": "string",
                            "description": "相对于 skill 根目录的文件路径。",
                        },
                    },
                    "required": ["relative_path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_skill_context",
                "description": "按问题检索指定文档处理方式(skill)的上下文片段。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "目标文档处理方式标识；不传时默认当前主处理方式。",
                        },
                        "query": {
                            "type": "string",
                            "description": "检索关键词或自然语言问题。",
                        },
                        "source_path": {
                            "type": "string",
                            "description": "可选。限定搜索的相对路径。",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 8,
                            "description": "最多返回多少条结果。",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_context",
                "description": "读取指定 chunk 正文并加入该 skill 的会话上下文。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "目标文档处理方式标识；不传时默认当前主处理方式。",
                        },
                        "chunk_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 6,
                        },
                    },
                    "required": ["chunk_ids"],
                    "additionalProperties": False,
                },
            },
        },
    ]

    declared_tools: list[dict[str, Any]] = []
    for skill_id in normalized_skill_ids:
        skill_interface = get_skill_interface(skill_id)
        for tool in skill_interface.tools:
            declared_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": compose_scoped_tool_name(skill_id, tool.name),
                        "description": f"[{skill_interface.display_name}] {tool.description}",
                        "parameters": tool.parameters,
                    },
                }
            )

    return [*builtin_tools, *declared_tools]


def _parse_tool_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    function_payload = tool_call.get("function")
    if not isinstance(function_payload, dict):
        return {}

    raw_arguments = function_payload.get("arguments")
    if isinstance(raw_arguments, dict):
        return raw_arguments

    if not isinstance(raw_arguments, str) or not raw_arguments.strip():
        return {}

    try:
        parsed_arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}

    if isinstance(parsed_arguments, dict):
        return parsed_arguments
    return {}


def _get_tool_name(tool_call: dict[str, Any]) -> str:
    function_payload = tool_call.get("function")
    if not isinstance(function_payload, dict):
        return ""

    name = function_payload.get("name")
    if isinstance(name, str):
        return name.strip()
    return ""


def _resolve_tool_scope(
    *,
    default_skill_id: str,
    tool_call: dict[str, Any],
) -> tuple[str, str]:
    raw_tool_name = _get_tool_name(tool_call)
    scoped_skill_id, base_tool_name = split_scoped_tool_name(raw_tool_name)
    arguments = _parse_tool_arguments(tool_call)
    argument_skill_id = str(arguments.get("skill_id", "")).strip()
    resolved_skill_id = scoped_skill_id or argument_skill_id or default_skill_id
    return resolved_skill_id, base_tool_name


def _format_declared_tool_default_name(
    tool: SkillToolConfig,
    arguments: dict[str, Any],
) -> str:
    attachment_config = tool.execution.attachment
    default_template = (
        attachment_config.default_name_template
        if attachment_config is not None
        else "{tool_name}-output.bin"
    )

    format_payload = {
        "tool_name": tool.name,
        **{
            key: value
            for key, value in arguments.items()
            if isinstance(value, (str, int, float))
        },
    }
    try:
        return default_template.format(**format_payload)
    except Exception:
        return f"{tool.name}-output.bin"


def _strip_wrapped_code_fence(value: str) -> str:
    """移除模型常见的 ```json / ```yaml 包裹。"""
    stripped_value = value.strip()
    if not stripped_value.startswith("```"):
        return stripped_value

    lines = stripped_value.splitlines()
    if len(lines) < 2:
        return stripped_value

    first_line = lines[0].strip()
    last_line = lines[-1].strip()
    if first_line.startswith("```") and last_line == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped_value


def _normalize_text_to_chaptered_document(value: str) -> dict[str, Any] | None:
    """把 Markdown/纯文本结构稿规整成通用的章节树结构。"""
    normalized = value.strip()
    if not normalized:
        return None

    lines = normalized.splitlines()
    root_sections: list[dict[str, Any]] = []
    stack: list[tuple[int, dict[str, Any]]] = []
    current_buffer: list[str] = []

    def flush_buffer_to(node: dict[str, Any] | None) -> None:
        nonlocal current_buffer
        if not current_buffer:
            return

        content = "\n".join(line.rstrip() for line in current_buffer).strip()
        current_buffer = []
        if not content:
            return

        if node is None:
            if root_sections:
                first_section = root_sections[0]
                existing = str(first_section.get("content", "")).strip()
                first_section["content"] = (
                    f"{content}\n\n{existing}".strip() if existing else content
                )
            else:
                root_sections.append(
                    {
                        "title": DEFAULT_STRUCTURED_TEXT_TITLE,
                        "content": content,
                        "sections": [],
                    }
                )
            return

        existing = str(node.get("content", "")).strip()
        node["content"] = f"{existing}\n\n{content}".strip() if existing else content

    for raw_line in lines:
        stripped_line = raw_line.strip()
        if not stripped_line:
            current_buffer.append("")
            continue

        if stripped_line.startswith("#"):
            heading_level = len(stripped_line) - len(stripped_line.lstrip("#"))
            heading_title = stripped_line[heading_level:].strip()
            if not heading_title:
                current_buffer.append(raw_line)
                continue

            current_node = stack[-1][1] if stack else None
            flush_buffer_to(current_node)

            section_node: dict[str, Any] = {
                "title": heading_title,
                "content": "",
                "sections": [],
            }

            while stack and stack[-1][0] >= heading_level:
                stack.pop()

            if stack:
                stack[-1][1].setdefault("sections", []).append(section_node)
            else:
                root_sections.append(section_node)

            stack.append((heading_level, section_node))
            continue

        current_buffer.append(raw_line)

    flush_buffer_to(stack[-1][1] if stack else None)

    if root_sections:
        return {"chapters": root_sections}

    return {
        "chapters": [
            {
                "title": DEFAULT_STRUCTURED_TEXT_TITLE,
                "content": normalized,
                "sections": [],
            }
        ]
    }


def _apply_json_file_text_normalizer(
    *,
    argument_name: str,
    normalized_text: str,
    text_normalizer: str | None,
) -> dict | list | None:
    """按声明式策略把文本规整成可序列化结构。"""
    if not text_normalizer:
        return None

    if text_normalizer == "chaptered_document":
        return _normalize_text_to_chaptered_document(normalized_text)

    raise ValueError(
        f"参数 `{argument_name}` 配置了不支持的 text_normalizer：{text_normalizer}。"
    )


def _coerce_json_file_argument(
    argument_name: str,
    argument_value: Any,
    *,
    text_normalizer: str | None = None,
) -> dict | list:
    """把 json_file 入参规整成可序列化的对象/数组。"""
    if isinstance(argument_value, (dict, list)):
        return argument_value

    if isinstance(argument_value, str):
        normalized = argument_value.strip()
        if not normalized:
            raise ValueError(f"参数 `{argument_name}` 不能为空字符串。")

        normalized = _strip_wrapped_code_fence(normalized)
        parsed_value: Any = normalized
        # 兼容模型把 JSON 对象当字符串、甚至双层字符串传回来的情况。
        for _ in range(2):
            if not isinstance(parsed_value, str):
                break
            try:
                parsed_value = json.loads(parsed_value)
            except json.JSONDecodeError:
                break

        if isinstance(parsed_value, (dict, list)):
            return parsed_value

        if yaml is not None:
            try:
                parsed_yaml = yaml.safe_load(normalized)
            except Exception:
                parsed_yaml = None
            if isinstance(parsed_yaml, (dict, list)):
                return parsed_yaml

        normalized_value = _apply_json_file_text_normalizer(
            argument_name=argument_name,
            normalized_text=normalized,
            text_normalizer=text_normalizer,
        )
        if isinstance(normalized_value, (dict, list)):
            return normalized_value

        raise ValueError(
            f"参数 `{argument_name}` 需要是对象或数组。当前收到字符串，且无法解析为 JSON/YAML"
            + (" 或当前声明的文本规整格式。" if text_normalizer else "。")
        )

    raise ValueError(
        f"参数 `{argument_name}` 需要是对象或数组，当前类型为 {type(argument_value).__name__}。"
    )


def _build_declared_tool_command(
    *,
    request: ChatStreamRequest,
    tool: SkillToolConfig,
    arguments: dict[str, Any],
    temp_dir_path: Path,
) -> tuple[list[str], str | None]:
    tool_path = _resolve_skill_relative_path(request.skill_id, tool.path)
    execution = tool.execution

    if execution.runtime != "python":
        raise ValueError(f"暂不支持的工具运行时：{execution.runtime}")

    command = [sys.executable, str(tool_path)]
    project_root = str(BACKEND_DIR.parent)
    skill_root = str(_get_skill_root(request.skill_id))

    for fixed_arg in execution.fixed_args:
        command.append(
            fixed_arg.format(
                project_root=project_root,
                skill_root=skill_root,
                temp_dir=str(temp_dir_path),
            )
        )

    attachment_output_name: str | None = None
    attachment_output_path: Path | None = None
    for argument_name, binding in execution.arg_bindings.items():
        if argument_name not in arguments:
            continue

        argument_value = arguments[argument_name]
        serializer = binding.serializer
        command.append(binding.flag)

        if serializer == "string":
            command.append(str(argument_value))
            continue

        if serializer == "json_file":
            normalized_json_value = _coerce_json_file_argument(
                argument_name,
                argument_value,
                text_normalizer=binding.text_normalizer,
            )
            json_file_path = temp_dir_path / f"{argument_name}.json"
            json_file_path.write_text(
                json.dumps(normalized_json_value, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            command.append(str(json_file_path))
            continue

        if serializer == "attachment_output_name":
            file_name = str(argument_value).strip() or _format_declared_tool_default_name(
                tool,
                arguments,
            )
            attachment_output_name = file_name
            attachment_output_path = temp_dir_path / file_name
            command.append(str(attachment_output_path))
            continue

        raise ValueError(f"暂不支持的参数序列化方式：{serializer}")

    if execution.attachment and attachment_output_path is None:
        attachment_output_name = _format_declared_tool_default_name(tool, arguments)
        attachment_output_path = temp_dir_path / attachment_output_name
        output_binding = next(
            (
                binding
                for binding in execution.arg_bindings.values()
                if binding.serializer == "attachment_output_name"
            ),
            None,
        )
        if output_binding is not None:
            command.extend([output_binding.flag, str(attachment_output_path)])

    return command, attachment_output_name


def _execute_declared_script_tool(
    *,
    request: ChatStreamRequest,
    tool: SkillToolConfig,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], list[ChatAttachment]]:
    if tool.kind != "script":
        return {
            "ok": False,
            "error": f"暂不支持的工具类型：{tool.kind}",
        }, []

    with tempfile.TemporaryDirectory(prefix="skill-tool-") as temp_dir:
        temp_dir_path = Path(temp_dir)
        command, attachment_output_name = _build_declared_tool_command(
            request=request,
            tool=tool,
            arguments=arguments,
            temp_dir_path=temp_dir_path,
        )

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            return {
                "ok": False,
                "error": stderr or stdout or "脚本执行失败。",
            }, []

        attachment_config = tool.execution.attachment
        if attachment_config is None:
            return {
                "ok": True,
                "stdout": completed.stdout.strip(),
            }, []

        resolved_output_name = attachment_output_name or _format_declared_tool_default_name(
            tool,
            arguments,
        )
        output_path = temp_dir_path / resolved_output_name
        if not output_path.is_file():
            return {
                "ok": False,
                "error": "脚本执行完成，但未找到输出文件。",
            }, []

        attachment = save_generated_attachment(
            source_path=output_path,
            conversation_id=request.conversation_id,
            skill_id=request.skill_id,
            output_name=resolved_output_name,
            mime_type=attachment_config.mime_type,
        )
        return {
            "ok": True,
            "attachment": attachment.model_dump(mode="json", by_alias=True),
            # 附件型工具只返回结构化结果，避免把本地临时路径日志暴露给模型后再回显给用户。
            "message": "文件已生成，请通过附件信息下载。",
        }, [attachment]


def execute_skill_tool_call(
    *,
    request: ChatStreamRequest,
    state: SkillConversationState,
    tool_call: dict[str, Any],
) -> tuple[dict[str, Any], list[ChatAttachment]]:
    """执行单个 tool call，并返回工具结果与产物列表。"""
    tool_name = _get_tool_name(tool_call)
    arguments = _parse_tool_arguments(tool_call)

    try:
        if tool_name == "list_skill_directory":
            relative_path = str(arguments.get("relative_path", "")).strip()
            return {
                "ok": True,
                "skill_id": request.skill_id,
                "relative_path": relative_path or ".",
                "entries": _list_directory_entries(request.skill_id, relative_path),
            }, []

        if tool_name == "read_skill_file":
            relative_path = str(arguments.get("relative_path", "")).strip()
            if not relative_path:
                return {
                    "ok": False,
                    "error": "relative_path 不能为空。",
                }, []

            return {
                "ok": True,
                "skill_id": request.skill_id,
                **_read_skill_file_content(request.skill_id, relative_path),
            }, []

        if tool_name == "search_skill_context":
            query = str(arguments.get("query", "")).strip()
            if not query:
                return {
                    "ok": False,
                    "error": "query 不能为空。",
                }, []

            source_path = str(arguments.get("source_path", "")).strip() or None
            raw_limit = arguments.get("limit", settings.skill_context_search_limit)
            limit = (
                raw_limit
                if isinstance(raw_limit, int) and 1 <= raw_limit <= 8
                else settings.skill_context_search_limit
            )
            chunks = search_skill_context_chunks(
                request.skill_id,
                query,
                exclude_chunk_ids=set(),
                limit=limit,
                source_path_contains=source_path,
            )
            return {
                "ok": True,
                "skill_id": request.skill_id,
                "query": query,
                "source_path": source_path,
                "chunks": [
                    {
                        "id": chunk.id,
                        "source_path": chunk.source_path,
                        "title": chunk.title,
                        "preview": chunk.preview,
                        "already_loaded": chunk.id in state.loaded_chunk_ids,
                    }
                    for chunk in chunks
                ],
            }, []

        if tool_name == "read_skill_context":
            raw_chunk_ids = arguments.get("chunk_ids", [])
            if not isinstance(raw_chunk_ids, list):
                return {
                    "ok": False,
                    "error": "chunk_ids 必须是字符串数组。",
                }, []

            chunk_ids = [
                str(chunk_id).strip()
                for chunk_id in raw_chunk_ids
                if isinstance(chunk_id, str) and str(chunk_id).strip()
            ]
            if not chunk_ids:
                return {
                    "ok": False,
                    "error": "chunk_ids 不能为空。",
                }, []

            loaded_chunks = get_skill_context_chunks_by_ids(request.skill_id, chunk_ids)
            next_chunk_ids = [
                chunk.id
                for chunk in loaded_chunks
                if chunk.id not in state.loaded_chunk_ids
            ]
            if next_chunk_ids:
                state.loaded_chunk_ids.extend(next_chunk_ids)

            return {
                "ok": True,
                "skill_id": request.skill_id,
                "loaded_chunk_ids": next_chunk_ids,
                "chunks": [
                    {
                        "id": chunk.id,
                        "source_path": chunk.source_path,
                        "title": chunk.title,
                        "content": chunk.content,
                    }
                    for chunk in loaded_chunks
                ],
            }, []

        try:
            declared_tool = get_skill_tool_config(request.skill_id, tool_name)
        except ValueError:
            return {
                "ok": False,
                "error": f"未知工具：{tool_name or '<empty>'}",
            }, []

        return _execute_declared_script_tool(
            request=request,
            tool=declared_tool,
            arguments=arguments,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "error": str(exc),
        }, []


def execute_scoped_skill_tool_call(
    *,
    request: ChatStreamRequest,
    states_by_skill: dict[str, SkillConversationState],
    default_skill_id: str,
    tool_call: dict[str, Any],
) -> tuple[dict[str, Any], list[ChatAttachment]]:
    """在多 skill 场景下执行工具调用，支持 `skill_id::tool_name` 名称空间。"""
    resolved_skill_id, base_tool_name = _resolve_tool_scope(
        default_skill_id=default_skill_id,
        tool_call=tool_call,
    )
    if resolved_skill_id not in states_by_skill:
        return {
            "ok": False,
            "error": f"未知或未激活的 skill：{resolved_skill_id}",
        }, []

    arguments = _parse_tool_arguments(tool_call)
    normalized_arguments = {
        key: value for key, value in arguments.items() if key != "skill_id"
    }
    function_payload = tool_call.get("function")
    normalized_tool_call = {
        "id": tool_call.get("id"),
        "type": tool_call.get("type"),
        "function": {
            "name": base_tool_name,
            "arguments": json.dumps(normalized_arguments, ensure_ascii=False),
        },
    }
    if isinstance(function_payload, dict):
        if "id" in function_payload:
            normalized_tool_call["function"]["id"] = function_payload["id"]  # pragma: no cover

    scoped_request = request.model_copy(update={"skill_id": resolved_skill_id})
    scoped_state = states_by_skill[resolved_skill_id]
    return execute_skill_tool_call(
        request=scoped_request,
        state=scoped_state,
        tool_call=normalized_tool_call,
    )
