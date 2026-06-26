import pytest

from doc_process_studio.skill.infrastructure.registry import (
    _read_skill_markdown_metadata,
    _read_yaml_interface_block,
    _strip_wrapped_text,
    get_skill_interface,
    list_skill_interfaces,
)


def test_strip_wrapped_text_double_quotes():
    assert _strip_wrapped_text('"hello"') == "hello"


def test_strip_wrapped_text_single_quotes():
    assert _strip_wrapped_text("'hello'") == "hello"


def test_strip_wrapped_text_no_quotes():
    assert _strip_wrapped_text("hello") == "hello"


def test_strip_wrapped_text_mismatched():
    assert _strip_wrapped_text('"hello') == '"hello'


def test_read_yaml_interface_block(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("interface:\n  display_name: 测试技能\n  skill_type: chat\n  default_prompt: 你是助手\n")
    result = _read_yaml_interface_block(config)
    assert result["display_name"] == "测试技能"
    assert result["skill_type"] == "chat"
    assert result["default_prompt"] == "你是助手"


def test_read_yaml_interface_block_no_interface(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("other_key: value\n")
    result = _read_yaml_interface_block(config)
    assert result == {}


def test_read_skill_markdown_metadata(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    md = skill_dir / "SKILL.md"
    md.write_text("---\nname: 测试技能\nskill_type: chat\n---\n# 内容\n")
    result = _read_skill_markdown_metadata(skill_dir)
    assert result["name"] == "测试技能"
    assert result["skill_type"] == "chat"


def test_read_skill_markdown_metadata_no_frontmatter(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    md = skill_dir / "SKILL.md"
    md.write_text("# No frontmatter\nContent here\n")
    result = _read_skill_markdown_metadata(skill_dir)
    assert result == {}


def test_read_skill_markdown_metadata_no_file(tmp_path):
    result = _read_skill_markdown_metadata(tmp_path / "nonexistent")
    assert result == {}


def test_list_skill_interfaces_returns_list():
    result = list_skill_interfaces()
    assert isinstance(result, list)


def test_get_skill_interface_valid():
    skills = list_skill_interfaces()
    if skills:
        skill = get_skill_interface(skills[0].id)
        assert skill.id == skills[0].id


def test_get_skill_interface_invalid():
    with pytest.raises(ValueError):
        get_skill_interface("nonexistent-skill-id-xyz")
