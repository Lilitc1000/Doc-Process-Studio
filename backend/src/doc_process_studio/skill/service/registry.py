import json
from functools import lru_cache
from pathlib import Path

from ..models.catalog import SkillInterfaceConfig, SkillToolConfig
from ..models.interaction import SkillInteractionConfig

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"


def _strip_wrapped_text(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {
        '"',
        "'",
    }:
        return cleaned[1:-1]
    return cleaned


def _read_yaml_interface_block(config_path: Path) -> dict[str, str]:
    interface_values: dict[str, str] = {}
    in_interface_block = False

    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        stripped_line = raw_line.strip()
        if not raw_line.startswith((" ", "\t")):
            in_interface_block = stripped_line == "interface:"
            continue

        if not in_interface_block:
            continue

        if ":" not in stripped_line:
            continue

        key, raw_value = stripped_line.split(":", 1)
        interface_values[key.strip()] = _strip_wrapped_text(raw_value)

    return interface_values


def _resolve_agent_config_path(skill_dir: Path) -> Path | None:
    candidate = skill_dir / "agents" / "config.yaml"
    if candidate.is_file():
        return candidate
    return None


def _read_skill_markdown_metadata(skill_dir: Path) -> dict[str, str]:
    """读取 SKILL.md 的 frontmatter 元数据（name/description 等）。"""
    skill_markdown_path = skill_dir / "SKILL.md"
    if not skill_markdown_path.is_file():
        return {}

    try:
        lines = skill_markdown_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    if not lines or lines[0].strip() != "---":
        return {}

    metadata: dict[str, str] = {}
    for raw_line in lines[1:]:
        stripped_line = raw_line.strip()
        if stripped_line == "---":
            break
        if not stripped_line or stripped_line.startswith("#"):
            continue
        if ":" not in stripped_line:
            continue

        key, raw_value = stripped_line.split(":", 1)
        normalized_key = key.strip()
        normalized_value = _strip_wrapped_text(raw_value)
        if normalized_key:
            metadata[normalized_key] = normalized_value.strip()

    return metadata


def _resolve_tools_config_path(skill_dir: Path) -> Path | None:
    candidate = skill_dir / "tools.json"
    if candidate.is_file():
        return candidate
    return None


def _resolve_interaction_config_path(skill_dir: Path) -> Path | None:
    candidate = skill_dir / "agents" / "interaction.json"
    if candidate.is_file():
        return candidate
    return None


def _load_declared_tools(skill_dir: Path) -> list[SkillToolConfig]:
    config_path = _resolve_tools_config_path(skill_dir)
    if config_path is None:
        return []

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    raw_tools = payload.get("tools") if isinstance(payload, dict) else None
    if not isinstance(raw_tools, list):
        return []

    declared_tools: list[SkillToolConfig] = []
    for raw_tool in raw_tools:
        if not isinstance(raw_tool, dict):
            continue
        try:
            declared_tools.append(SkillToolConfig.model_validate(raw_tool))
        except Exception:
            continue
    return declared_tools


def _load_interaction_config(skill_dir: Path) -> SkillInteractionConfig | None:
    config_path = _resolve_interaction_config_path(skill_dir)
    if config_path is None:
        return None

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    try:
        config = SkillInteractionConfig.model_validate(payload)
    except Exception:
        return None

    if not config.enabled or not config.steps:
        return None
    return config


def _build_skill_interface_config(skill_dir: Path) -> SkillInterfaceConfig | None:
    config_path = _resolve_agent_config_path(skill_dir)
    if config_path is None:
        return None

    interface_values = _read_yaml_interface_block(config_path)
    skill_markdown_metadata = _read_skill_markdown_metadata(skill_dir)
    display_name = (
        interface_values.get("display_name", "").strip()
        or skill_markdown_metadata.get("name", "").strip()
    )
    skill_type = (
        interface_values.get("skill_type", "").strip()
        or skill_markdown_metadata.get("skill_type", "").strip()
        or "chat"
    )
    default_prompt = interface_values.get("default_prompt", "").strip()
    short_description = (
        interface_values.get("short_description", "").strip()
        or skill_markdown_metadata.get("description", "").strip()
    )

    if not display_name or not default_prompt:
        return None

    return SkillInterfaceConfig(
        id=skill_dir.name,
        display_name=display_name,
        skill_type=skill_type,
        short_description=short_description,
        default_prompt=default_prompt,
        tools=_load_declared_tools(skill_dir),
    )


@lru_cache(maxsize=32)
def _load_skill_interaction_config_by_id(skill_id: str) -> SkillInteractionConfig | None:
    skill_dir = SKILLS_DIR / skill_id
    if not skill_dir.is_dir():
        return None
    return _load_interaction_config(skill_dir)


@lru_cache(maxsize=1)
def load_skill_registry() -> list[SkillInterfaceConfig]:
    if not SKILLS_DIR.exists():
        return []

    skills: list[SkillInterfaceConfig] = []
    for skill_dir in sorted(SKILLS_DIR.iterdir(), key=lambda item: item.name):
        if not skill_dir.is_dir():
            continue

        skill_config = _build_skill_interface_config(skill_dir)
        if skill_config is not None:
            skills.append(skill_config)

    return skills


def list_skill_interfaces() -> list[SkillInterfaceConfig]:
    return list(load_skill_registry())


def get_skill_interface(skill_id: str) -> SkillInterfaceConfig:
    normalized_skill_id = skill_id.strip()
    for skill in load_skill_registry():
        if skill.id == normalized_skill_id:
            return skill

    available_skill_ids = ", ".join(skill.id for skill in load_skill_registry())
    raise ValueError(
        f"未找到 skill `{normalized_skill_id}`。当前可用 skills: {available_skill_ids}"
    )


def get_skill_tool_config(skill_id: str, tool_name: str) -> SkillToolConfig:
    skill_interface = get_skill_interface(skill_id)
    normalized_tool_name = tool_name.strip()
    for tool in skill_interface.tools:
        if tool.name == normalized_tool_name:
            return tool

    available_tool_names = ", ".join(tool.name for tool in skill_interface.tools)
    raise ValueError(
        f"未找到 skill `{skill_id}` 的工具 `{normalized_tool_name}`。当前可用工具: {available_tool_names}"
    )


def get_skill_interaction_config(skill_id: str) -> SkillInteractionConfig | None:
    normalized_skill_id = skill_id.strip()
    if not normalized_skill_id:
        return None
    return _load_skill_interaction_config_by_id(normalized_skill_id)
