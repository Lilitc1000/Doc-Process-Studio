from functools import lru_cache
from pathlib import Path

from ..models.skills import SkillInterfaceConfig

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
DEFAULT_SKILL_ID = "document-assistant"


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
    agents_dir = skill_dir / "agents"
    for candidate_name in ("openai.yml", "openai.yaml"):
        candidate = agents_dir / candidate_name
        if candidate.is_file():
            return candidate
    return None


def _build_skill_interface_config(skill_dir: Path) -> SkillInterfaceConfig | None:
    config_path = _resolve_agent_config_path(skill_dir)
    if config_path is None:
        return None

    interface_values = _read_yaml_interface_block(config_path)
    display_name = interface_values.get("display_name", "").strip()
    default_prompt = interface_values.get("default_prompt", "").strip()

    if not display_name or not default_prompt:
        return None

    return SkillInterfaceConfig(
        id=skill_dir.name,
        display_name=display_name,
        short_description=interface_values.get("short_description", "").strip(),
        default_prompt=default_prompt,
    )


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


def get_default_skill_id() -> str:
    skill_ids = {skill.id for skill in load_skill_registry()}
    if DEFAULT_SKILL_ID in skill_ids:
        return DEFAULT_SKILL_ID
    if skill_ids:
        return load_skill_registry()[0].id
    return DEFAULT_SKILL_ID


def get_skill_interface(skill_id: str) -> SkillInterfaceConfig:
    normalized_skill_id = skill_id.strip()
    for skill in load_skill_registry():
        if skill.id == normalized_skill_id:
            return skill

    available_skill_ids = ", ".join(skill.id for skill in load_skill_registry())
    raise ValueError(
        f"未找到 skill `{normalized_skill_id}`。当前可用 skills: {available_skill_ids}"
    )
