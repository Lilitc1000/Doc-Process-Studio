import json
from pathlib import Path

from doc_process_studio.skill.models.catalog import SkillToolConfig
from doc_process_studio.skill.models.interaction import SkillInteractionConfig
from doc_process_studio.skill.service.registry import (
    SKILLS_DIR,
    get_skill_interface,
    get_skill_interaction_config,
    list_skill_interfaces,
)


def _resolve_tools_file(skill_dir: Path) -> Path | None:
    candidate = skill_dir / "tools.json"
    if candidate.is_file():
        return candidate
    return None


def _resolve_interaction_file(skill_dir: Path) -> Path | None:
    candidate = skill_dir / "agents" / "interaction.json"
    if candidate.is_file():
        return candidate
    return None


def _resolve_config_file(skill_dir: Path) -> Path | None:
    candidate = skill_dir / "agents" / "config.yaml"
    if candidate.is_file():
        return candidate
    return None


def test_all_skill_dirs_are_registered_and_have_config() -> None:
    skill_dirs = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())
    assert skill_dirs, "skills 目录为空，至少应有一个 skill。"

    registry_skill_ids = {skill.id for skill in list_skill_interfaces()}
    dir_skill_ids = {path.name for path in skill_dirs}

    # 目录中的所有 skill 都应进入注册表，否则说明某个 config 配置缺失或解析失败。
    assert registry_skill_ids == dir_skill_ids

    for skill_dir in skill_dirs:
        config_file = _resolve_config_file(skill_dir)
        assert config_file is not None, f"{skill_dir.name} 缺少 agents/config.yaml"

        skill_interface = get_skill_interface(skill_dir.name)
        assert skill_interface.display_name.strip() != ""
        assert skill_interface.default_prompt.strip() != ""


def test_all_skill_declared_configs_are_valid() -> None:
    for skill_dir in sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir()):
        tools_file = _resolve_tools_file(skill_dir)
        if tools_file is not None:
            tools_payload = json.loads(tools_file.read_text(encoding="utf-8"))
            assert isinstance(tools_payload, dict), f"{tools_file} 必须是 JSON 对象。"
            raw_tools = tools_payload.get("tools")
            assert isinstance(raw_tools, list), f"{tools_file} 缺少 tools 数组。"
            for raw_tool in raw_tools:
                SkillToolConfig.model_validate(raw_tool)

        interaction_file = _resolve_interaction_file(skill_dir)
        if interaction_file is not None:
            interaction_payload = json.loads(interaction_file.read_text(encoding="utf-8"))
            config = SkillInteractionConfig.model_validate(interaction_payload)
            runtime_config = get_skill_interaction_config(skill_dir.name)
            if config.enabled and config.steps:
                assert runtime_config is not None
            else:
                assert runtime_config is None
