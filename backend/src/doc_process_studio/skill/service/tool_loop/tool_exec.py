import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

from ....chat.schemas.attachment import ChatAttachment
from ....chat.schemas.request import ChatStreamRequest
from ....chat.service.attachments import save_generated_attachment
from ....core.config import BACKEND_DIR, settings
from ....shared.tool_args import parse_tool_arguments
from ...schemas.catalog import SkillToolConfig
from ...schemas.runtime import SkillConversationState
from ..context import get_skill_context_chunks_by_ids, search_skill_context_chunks
from ..registry import get_skill_tool_config
from .skill_files import (
    DEFAULT_STRUCTURED_TEXT_TITLE,
    _get_skill_root,
    _get_tool_name,
    _list_directory_entries,
    _primary_skill_id,
    _read_skill_file_content,
    _resolve_search_limit_bounds,
    _resolve_skill_relative_path,
    _resolve_tool_scope,
)
from .tool_args import (
    _build_builtin_tool_parameters,
    _normalize_builtin_tool_arguments,
    _validate_tool_arguments_schema,
)

try:
    import yaml as _yaml

    yaml_module: ModuleType | None = _yaml
except ModuleNotFoundError:
    yaml_module = None

try:
    import resource as _resource

    resource_module: ModuleType | None = _resource
except ModuleNotFoundError:
    resource_module = None

logger = logging.getLogger(__name__)


def _enforce_declared_tool_security_policy(
    *,
    request: ChatStreamRequest,
    tool: SkillToolConfig,
) -> None:
    security = tool.security
    if security is None:
        return

    risk_level = str(security.risk_level).strip().lower() or "low"
    policy = settings.skill_sensitive_operation_policy

    if policy == "confirm" and security.requires_confirmation and not request.confirm_sensitive_actions:
        raise ValueError(f"工具 `{tool.name}` 被标记为需要确认，当前请求未授权执行敏感操作。")

    if policy == "deny_high" and risk_level == "high":
        raise ValueError(f"工具 `{tool.name}` 风险等级为 high，当前策略禁止执行。")


def _build_subprocess_preexec(*, skill_root: Path) -> Callable[[], None] | None:
    if resource_module is None:
        return None

    cpu_seconds = max(1, settings.skill_tool_script_cpu_seconds)
    memory_bytes = max(64, settings.skill_tool_script_memory_limit_mb) * 1024 * 1024
    output_bytes = max(8, settings.skill_tool_script_output_limit_mb) * 1024 * 1024

    def _preexec() -> None:
        os.chdir(skill_root)
        assert resource_module is not None
        resource_module.setrlimit(resource_module.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource_module.setrlimit(resource_module.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource_module.setrlimit(resource_module.RLIMIT_FSIZE, (output_bytes, output_bytes))

    return _preexec


def _format_declared_tool_default_name(
    tool: SkillToolConfig,
    arguments: dict[str, Any],
) -> str:
    attachment_config = tool.execution.attachment
    default_template = (
        attachment_config.default_name_template if attachment_config is not None else "{tool_name}-output.bin"
    )

    format_payload = {
        "tool_name": tool.name,
        **{key: value for key, value in arguments.items() if isinstance(value, (str, int, float))},
    }
    try:
        return default_template.format(**format_payload)
    except Exception:
        logger.debug("Failed to format output name template: %s", default_template)
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
                first_section["content"] = f"{content}\n\n{existing}".strip() if existing else content
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
) -> dict[str, Any] | list[Any] | None:
    """按声明式策略把文本规整成可序列化结构。"""
    if not text_normalizer:
        return None

    if text_normalizer == "chaptered_document":
        return _normalize_text_to_chaptered_document(normalized_text)

    raise ValueError(f"参数 `{argument_name}` 配置了不支持的 text_normalizer：{text_normalizer}。")


def _try_parse_json_like_value(raw_text: str) -> dict[str, Any] | list[Any] | None:
    """尝试解析 JSON 文本（含双重编码场景）。"""
    parsed_value: Any = raw_text
    for _ in range(2):
        if not isinstance(parsed_value, str):
            break
        try:
            parsed_value = json.loads(parsed_value)
        except json.JSONDecodeError:
            return None

    if isinstance(parsed_value, (dict, list)):
        return parsed_value
    return None


def _normalize_json_like_punctuation(text: str) -> str:
    """把 JSON 结构符号中的中文标点规整为英文标点（仅在字符串外生效）。"""
    normalized_chars: list[str] = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            normalized_chars.append(ch)
            escape_next = False
            continue

        if ch == "\\" and in_string:
            normalized_chars.append(ch)
            escape_next = True
            continue

        if ch == '"':
            normalized_chars.append(ch)
            in_string = not in_string
            continue

        if not in_string:
            if ch == "，":
                normalized_chars.append(",")
                continue
            if ch == "：":
                normalized_chars.append(":")
                continue

        normalized_chars.append(ch)

    return "".join(normalized_chars)


def _coerce_json_file_argument(
    argument_name: str,
    argument_value: Any,
    *,
    text_normalizer: str | None = None,
) -> dict[str, Any] | list[Any]:
    """把 json_file 入参规整成可序列化的对象/数组。"""
    if isinstance(argument_value, (dict, list)):
        return argument_value

    if isinstance(argument_value, str):
        normalized = argument_value.strip()
        if not normalized:
            raise ValueError(f"参数 `{argument_name}` 不能为空字符串。")

        normalized = _strip_wrapped_code_fence(normalized)
        parsed_json_value = _try_parse_json_like_value(normalized)
        if isinstance(parsed_json_value, (dict, list)):
            return parsed_json_value

        json_like = normalized.startswith(("[", "{"))
        if json_like:
            normalized_punctuation = _normalize_json_like_punctuation(normalized)
            if normalized_punctuation != normalized:
                parsed_with_punctuation_fix = _try_parse_json_like_value(normalized_punctuation)
                if isinstance(parsed_with_punctuation_fix, (dict, list)):
                    return parsed_with_punctuation_fix

                repaired_with_punctuation_fix = _try_repair_truncated_json(normalized_punctuation)
                if isinstance(repaired_with_punctuation_fix, (dict, list)):
                    return repaired_with_punctuation_fix

            repaired = _try_repair_truncated_json(normalized)
            if isinstance(repaired, (dict, list)):
                return repaired

        if yaml_module is not None:
            try:
                parsed_yaml = yaml_module.safe_load(normalized)
            except Exception:
                logger.debug("Failed to parse YAML tool arguments")
                parsed_yaml = None
            if isinstance(parsed_yaml, (dict, list)):
                return parsed_yaml

        if json_like:
            raise ValueError(
                f"参数 `{argument_name}` 看起来是 JSON，但解析失败。请检查是否存在中文逗号/冒号、缺失引号或截断。"
            )

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

    raise ValueError(f"参数 `{argument_name}` 需要是对象或数组，当前类型为 {type(argument_value).__name__}。")


_HEADING_PATTERN = re.compile(
    r"^(?P<num>\d+(?:\.\d+)*\.?)\s+(?P<title>\S.*)$",
)


def _try_repair_truncated_json(text: str) -> dict[str, Any] | list[Any] | None:
    """尝试修复模型输出被截断的 JSON 字符串。

    模型在生成长 JSON 时可能超出 token 限制导致截断，
    例如缺少闭合的 ] 或 }。本函数尝试补全缺失的括号。
    """
    stripped = text.strip()
    if not stripped or stripped[0] not in ("[", "{"):
        return None

    try:
        json.loads(stripped)
        return None
    except json.JSONDecodeError:
        pass

    open_stack: list[str] = []
    in_string = False
    escape_next = False

    for ch in stripped:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "[":
            open_stack.append("]")
        elif ch == "{":
            open_stack.append("}")
        elif ch in ("]", "}") and open_stack and open_stack[-1] == ch:
            open_stack.pop()

    if in_string:
        stripped += '"'

    if stripped.endswith(","):
        stripped = stripped[:-1]

    if stripped.endswith(":"):
        stripped = stripped[:-1]

    open_stack2: list[str] = []
    in_str2 = False
    esc2 = False
    for ch in stripped:
        if esc2:
            esc2 = False
            continue
        if ch == "\\" and in_str2:
            esc2 = True
            continue
        if ch == '"':
            in_str2 = not in_str2
            continue
        if in_str2:
            continue
        if ch == "[":
            open_stack2.append("]")
        elif ch == "{":
            open_stack2.append("}")
        elif ch in ("]", "}") and open_stack2 and open_stack2[-1] == ch:
            open_stack2.pop()

    closing = "".join(reversed(open_stack2))
    repaired = stripped + closing

    try:
        result = json.loads(repaired)
        if isinstance(result, (dict, list)):
            return result
    except (json.JSONDecodeError, Exception):
        logger.debug("Failed to repair truncated JSON")
        pass

    return None


def _restructure_doc_plan(value: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
    """修复模型输出的 doc_plan 结构。

    常见问题：
    1. 模型把子节标题大纲平铺在 content 字段中，而不是用 sections 嵌套。
    2. 模型把同一章拆成两个条目：一个带标题+摘要（无 sections），
       一个带内容+子节（无 title）。后者会被 render_custom_node 跳过。
    本函数检测这些情况并自动修复。
    """
    chapters = value.get("chapters", value) if isinstance(value, dict) else value
    if not isinstance(chapters, list):
        return value

    restructured = [_restructure_section(ch) for ch in chapters]
    merged = _merge_titleless_chapters(restructured)
    if isinstance(value, dict) and "chapters" in value:
        value["chapters"] = merged
        return value
    return merged


def _merge_titleless_chapters(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将无标题的章节合并到前一个有标题的章节中。"""
    if not chapters:
        return chapters

    result: list[dict] = []
    for ch in chapters:
        title = str(ch.get("title") or "").strip()
        has_title = bool(title)

        if has_title or not result:
            result.append(ch)
            continue

        prev = result[-1]

        ch_sections = ch.get("sections") or []
        ch_content = str(ch.get("content") or "").strip()

        if ch_sections:
            existing_sections = prev.get("sections") or []
            prev["sections"] = [*existing_sections, *ch_sections]
            if ch_content and not prev.get("content"):
                prev["content"] = ch_content
        elif ch_content:
            existing_content = str(prev.get("content") or "").strip()
            if existing_content:
                prev["content"] = f"{existing_content}\n\n{ch_content}"
            else:
                prev["content"] = ch_content

    return result


def _restructure_section(section: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(section, dict):
        return section

    if isinstance(section.get("sections"), list):
        section["sections"] = [_restructure_section(s) for s in section["sections"]]

    content = section.get("content")
    if not isinstance(content, str):
        return section

    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if not lines:
        return section

    heading_lines: list[tuple[str, str]] = []
    non_heading_lines: list[str] = []
    for line in lines:
        m = _HEADING_PATTERN.match(line)
        if m:
            heading_lines.append((m.group("num"), m.group("title")))
        else:
            non_heading_lines.append(line)

    if len(heading_lines) < 2:
        return section

    section["content"] = "\n".join(non_heading_lines) if non_heading_lines else ""
    existing_sections = section.get("sections") or []
    section["sections"] = [
        *existing_sections,
        *[{"title": f"{num} {title}", "content": "", "sections": []} for num, title in heading_lines],
    ]
    return section


def _build_declared_tool_command(
    *,
    request: ChatStreamRequest,
    tool: SkillToolConfig,
    arguments: dict[str, Any],
    temp_dir_path: Path,
) -> tuple[list[str], str | None]:
    tool_path = _resolve_skill_relative_path(_primary_skill_id(request), tool.path)
    execution = tool.execution

    if execution.runtime != "python":
        raise ValueError(f"暂不支持的工具运行时：{execution.runtime}")

    command = [sys.executable, str(tool_path)]
    project_root = str(BACKEND_DIR.parent)
    skill_root = str(_get_skill_root(_primary_skill_id(request)))

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
            if argument_name == "doc_plan" and isinstance(normalized_json_value, (dict, list)):
                normalized_json_value = _restructure_doc_plan(normalized_json_value)
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
            (binding for binding in execution.arg_bindings.values() if binding.serializer == "attachment_output_name"),
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
        skill_root = _get_skill_root(_primary_skill_id(request))

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(skill_root),
                timeout=max(1, settings.skill_tool_script_timeout_seconds),
                preexec_fn=_build_subprocess_preexec(skill_root=skill_root),
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONUNBUFFERED": "1",
                    "TMPDIR": str(temp_dir_path),
                },
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": (
                    f"脚本执行超时，已中止。 超时阈值：{max(1, settings.skill_tool_script_timeout_seconds)} 秒。"
                ),
            }, []

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
            skill_id=_primary_skill_id(request),
            output_name=resolved_output_name,
            mime_type=attachment_config.mime_type,
        )
        return {
            "ok": True,
            "attachment": attachment.model_dump(mode="json"),
            # 附件型工具只返回结构化结果，避免把本地临时路径日志暴露给模型后再回显给用户。
            "message": "文件已生成，请通过附件信息下载。",
        }, [attachment]


async def _execute_builtin_tool(
    *,
    request: ChatStreamRequest,
    state: SkillConversationState,
    tool_name: str,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], list[ChatAttachment]] | None:
    if tool_name == "list_skill_directory":
        relative_path = str(arguments.get("relative_path", "")).strip()
        return {
            "ok": True,
            "skill_id": _primary_skill_id(request),
            "relative_path": relative_path or ".",
            "entries": _list_directory_entries(_primary_skill_id(request), relative_path),
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
            "skill_id": _primary_skill_id(request),
            **_read_skill_file_content(_primary_skill_id(request), relative_path),
        }, []

    if tool_name == "search_skill_context":
        query = str(arguments.get("query", "")).strip()
        if not query:
            return {
                "ok": False,
                "error": "query 不能为空。",
            }, []

        source_path = str(arguments.get("source_path", "")).strip() or None
        default_search_limit, max_search_limit = _resolve_search_limit_bounds()
        raw_limit = arguments.get("limit", default_search_limit)
        limit = raw_limit if isinstance(raw_limit, int) and 1 <= raw_limit <= max_search_limit else default_search_limit
        chunks = await search_skill_context_chunks(
            _primary_skill_id(request),
            query,
            exclude_chunk_ids=set(),
            limit=limit,
            source_path_contains=source_path,
            reranker_model=(request.reranker_model or request.model),
        )
        return {
            "ok": True,
            "skill_id": _primary_skill_id(request),
            "query": query,
            "source_path": source_path,
            "limit": limit,
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
            str(chunk_id).strip() for chunk_id in raw_chunk_ids if isinstance(chunk_id, str) and str(chunk_id).strip()
        ]
        if not chunk_ids:
            return {
                "ok": False,
                "error": "chunk_ids 不能为空。",
            }, []

        loaded_chunks = get_skill_context_chunks_by_ids(_primary_skill_id(request), chunk_ids)
        next_chunk_ids = [chunk.id for chunk in loaded_chunks if chunk.id not in state.loaded_chunk_ids]
        if next_chunk_ids:
            state.loaded_chunk_ids.extend(next_chunk_ids)

        return {
            "ok": True,
            "skill_id": _primary_skill_id(request),
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

    if tool_name == "search_knowledge_base":
        query = str(arguments.get("query", "")).strip()
        if not query:
            return {
                "ok": False,
                "error": "query 不能为空。",
            }, []

        primary_id = _primary_skill_id(request)
        project_name = ""
        if primary_id.startswith("kb:"):
            project_name = primary_id[3:]

        if not project_name:
            return {
                "ok": False,
                "error": "未指定知识库项目。",
            }, []

        from ....core.config import settings as app_settings
        from ....knowledge_base.service.embedding import embed_texts
        from ....knowledge_base.service.qdrant_service import search_knowledge_base as kb_search

        vectors = await embed_texts([query])
        if not vectors or not vectors[0]:
            return {
                "ok": False,
                "error": "向量化查询失败。",
            }, []

        results = kb_search(project_name, vectors[0], top_k=app_settings.kb_search_top_k)
        kb_chunks: list[dict[str, Any]] = []
        for hit in results:
            payload = hit.get("payload", {})
            page_number = payload.get("page_number")
            section_title = payload.get("section_title")
            sheet_name = payload.get("sheet_name")
            file_name = payload.get("file_name", "")
            file_path = payload.get("file_path", "")
            content_type = payload.get("content_type", "text")

            source_parts: list[str] = []
            if file_path:
                source_parts.append(file_path)
            if file_name:
                source_parts.append(file_name)
            source_label = "/".join(source_parts) if source_parts else "未知文档"

            location_parts: list[str] = []
            if page_number is not None:
                location_parts.append(f"第{page_number}页")
            if section_title:
                location_parts.append(section_title)
            if sheet_name:
                location_parts.append(f"Sheet: {sheet_name}")
            if content_type == "table":
                location_parts.append("表格")
            elif content_type == "ocr":
                location_parts.append("扫描页")
            elif content_type == "mixed":
                location_parts.append("混合内容页")
            location_label = ", ".join(location_parts)

            kb_chunks.append(
                {
                    "content": payload.get("content", ""),
                    "source": source_label,
                    "location": location_label,
                    "page_number": page_number,
                    "section_title": section_title,
                    "sheet_name": sheet_name,
                    "file_name": file_name,
                    "file_path": file_path,
                    "content_type": content_type,
                    "score": hit.get("score", 0.0),
                }
            )

        return {
            "ok": True,
            "project_name": project_name,
            "query": query,
            "chunks": kb_chunks,
        }, []

    return None


async def execute_skill_tool_call(
    *,
    request: ChatStreamRequest,
    state: SkillConversationState,
    tool_call: dict[str, Any],
) -> tuple[dict[str, Any], list[ChatAttachment]]:
    tool_name = _get_tool_name(tool_call)
    raw_arguments = parse_tool_arguments(tool_call)
    arguments = _normalize_builtin_tool_arguments(
        tool_name=tool_name,
        arguments=raw_arguments,
    )

    try:
        builtin_parameters = _build_builtin_tool_parameters(tool_name)
        if builtin_parameters is not None:
            _validate_tool_arguments_schema(
                tool_name=tool_name,
                arguments=arguments,
                parameters=builtin_parameters,
            )

        builtin_result = await _execute_builtin_tool(
            request=request,
            state=state,
            tool_name=tool_name,
            arguments=arguments,
        )
        if builtin_result is not None:
            return builtin_result

        try:
            declared_tool = get_skill_tool_config(_primary_skill_id(request), tool_name)
        except ValueError:
            return {
                "ok": False,
                "error": f"未知工具：{tool_name or '<empty>'}",
            }, []

        _validate_tool_arguments_schema(
            tool_name=tool_name,
            arguments=arguments,
            parameters=declared_tool.parameters,
        )
        _enforce_declared_tool_security_policy(
            request=request,
            tool=declared_tool,
        )
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


async def execute_scoped_skill_tool_call(
    *,
    request: ChatStreamRequest,
    states_by_skill: dict[str, SkillConversationState],
    tool_call: dict[str, Any],
) -> tuple[dict[str, Any], list[Any]]:
    default_skill_id = _primary_skill_id(request)
    resolved_skill_id, base_tool_name = _resolve_tool_scope(
        default_skill_id=default_skill_id,
        tool_call=tool_call,
    )

    if resolved_skill_id not in states_by_skill:
        return {"ok": False, "error": f"未知或未激活的 skill：{resolved_skill_id}"}, []

    arguments = parse_tool_arguments(tool_call)
    normalized_arguments = {key: value for key, value in arguments.items() if key != "skill_id"}

    function_payload = tool_call.get("function")
    normalized_tool_call = {
        "id": tool_call.get("id"),
        "type": tool_call.get("type"),
        "function": {
            "name": base_tool_name,
            "arguments": json.dumps(normalized_arguments, ensure_ascii=False),
        },
    }

    if isinstance(function_payload, dict) and "id" in function_payload:
        func_dict = normalized_tool_call["function"]
        if isinstance(func_dict, dict):
            func_dict["id"] = function_payload["id"]

    scoped_request = request.model_copy(update={"skill_id": resolved_skill_id})
    scoped_state = states_by_skill[resolved_skill_id]

    return await execute_skill_tool_call(
        request=scoped_request,
        state=scoped_state,
        tool_call=normalized_tool_call,
    )
