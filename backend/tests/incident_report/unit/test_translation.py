import asyncio

import doc_process_studio.incident_report.service.translation as translation_module
from doc_process_studio.incident_report.service.translation import (
    _collect_translation_targets,
    _set_nested_string_value,
    _should_skip_translation,
    stable_payload_hash,
    translation_cache_get,
    translation_cache_key,
    translation_cache_set,
)


def test_stable_payload_hash_deterministic():
    payload = {"a": 1, "b": "hello"}
    h1 = stable_payload_hash(payload)
    h2 = stable_payload_hash(payload)
    assert h1 == h2


def test_stable_payload_hash_different_payloads():
    h1 = stable_payload_hash({"a": 1})
    h2 = stable_payload_hash({"a": 2})
    assert h1 != h2


def test_translation_cache_key_format():
    key = translation_cache_key(model_name="test-model", source_text="hello")
    assert "test-model" in key
    assert ":" in key


def test_translation_cache_set_and_get():
    translation_module._TRANSLATION_CACHE.clear()
    key = "test-key-cache"
    translation_cache_set(key=key, value="translated")
    result = translation_cache_get(key)
    assert result == "translated"


def test_translation_cache_get_missing():
    translation_module._TRANSLATION_CACHE.clear()
    result = translation_cache_get("nonexistent-key")
    assert result is None


def test_translation_cache_eviction():
    translation_module._TRANSLATION_CACHE.clear()
    for i in range(4100):
        translation_cache_set(key=f"key-{i}", value=f"value-{i}")
    assert len(translation_module._TRANSLATION_CACHE) <= 4096


def test_should_skip_translation_date_key():
    assert _should_skip_translation(["fault_date"], "2026-04-08") is True


def test_should_skip_translation_reference_no_key():
    assert _should_skip_translation(["reference_no"], "DAS-001") is True


def test_should_skip_translation_normal_key():
    assert _should_skip_translation(["description"], "some text") is False


def test_should_skip_translation_data_image():
    assert _should_skip_translation(["image"], "data:image/png;base64,AAA") is True


def test_should_skip_translation_empty_path():
    assert _should_skip_translation([], "text") is False


def test_collect_translation_targets_dict():
    targets: dict[str, str] = {}
    _collect_translation_targets(
        {"description": "中文描述", "reference_no": "DAS-001"},
        path=[],
        targets=targets,
    )
    assert "description" in targets
    assert "reference_no" not in targets


def test_collect_translation_targets_nested():
    targets: dict[str, str] = {}
    _collect_translation_targets(
        {"body": {"description": "中文描述"}},
        path=[],
        targets=targets,
    )
    assert "body.description" in targets


def test_collect_translation_targets_list():
    targets: dict[str, str] = {}
    _collect_translation_targets(
        ["中文项目1", "English item"],
        path=[],
        targets=targets,
    )
    assert "0" in targets
    assert "1" not in targets


def test_collect_translation_targets_skips_non_cjk():
    targets: dict[str, str] = {}
    _collect_translation_targets(
        {"description": "English only text"},
        path=[],
        targets=targets,
    )
    assert len(targets) == 0


def test_collect_translation_targets_skips_empty():
    targets: dict[str, str] = {}
    _collect_translation_targets(
        {"description": ""},
        path=[],
        targets=targets,
    )
    assert len(targets) == 0


def test_set_nested_string_value_dict():
    payload = {"a": {"b": "old"}}
    result = _set_nested_string_value(payload, "a.b", "new")
    assert result is True
    assert payload["a"]["b"] == "new"


def test_set_nested_string_value_list():
    payload = ["old", "second"]
    result = _set_nested_string_value(payload, "0", "new")
    assert result is True
    assert payload[0] == "new"


def test_set_nested_string_value_missing_key():
    payload = {"a": "value"}
    result = _set_nested_string_value(payload, "b", "new")
    assert result is False


def test_set_nested_string_value_empty_path():
    result = _set_nested_string_value({}, "", "new")
    assert result is False


def test_set_nested_string_value_list_non_numeric_index():
    payload = ["a", "b"]
    result = _set_nested_string_value(payload, "x", "new")
    assert result is False


def test_set_nested_string_value_out_of_range():
    payload = ["a"]
    result = _set_nested_string_value(payload, "5", "new")
    assert result is False


def test_translate_report_data_skips_when_no_translator(monkeypatch):
    translation_module._TRANSLATION_CACHE.clear()
    monkeypatch.setattr(translation_module, "GoogleTranslator", None)
    report_data = {"description": "中文描述"}
    result = asyncio.run(
        translation_module.translate_report_data_to_english(report_data=report_data)
    )
    assert result == report_data
