from pathlib import Path
from typing import Any

from ....chat.schemas.request import ChatStreamRequest
from ....core.config import settings
from ....shared.tool_args import parse_tool_arguments
from ..registry import SKILLS_DIR

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


def _primary_skill_id(request: ChatStreamRequest) -> str:
    if request.selected_skill_ids:
        return request.selected_skill_ids[0]
    return ""


def _resolve_search_limit_bounds() -> tuple[int, int]:
    default_limit = max(1, int(settings.skill_context_search_limit))
    max_limit = max(default_limit, int(settings.skill_context_search_limit_max))
    return default_limit, max_limit


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
    arguments = parse_tool_arguments(tool_call)
    argument_skill_id = str(arguments.get("skill_id", "")).strip()
    resolved_skill_id = scoped_skill_id or argument_skill_id or default_skill_id
    return resolved_skill_id, base_tool_name

