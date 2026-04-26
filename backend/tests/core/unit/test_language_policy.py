import asyncio

import doc_process_studio.core.language_policy as language_policy_module
from doc_process_studio.core.language_policy import (
    normalize_language_code,
    describe_language,
    detect_language_with_model,
    verify_text_language_with_model,
)


def test_normalize_language_code_zh_variants():
    assert normalize_language_code("zh") == "zh"
    assert normalize_language_code("zh-cn") == "zh"
    assert normalize_language_code("zh-hans") == "zh"
    assert normalize_language_code("chinese") == "zh"
    assert normalize_language_code("中文") == "zh"
    assert normalize_language_code("汉语") == "zh"
    assert normalize_language_code("简体中文") == "zh"


def test_normalize_language_code_en_variants():
    assert normalize_language_code("en") == "en"
    assert normalize_language_code("en-us") == "en"
    assert normalize_language_code("en-gb") == "en"
    assert normalize_language_code("english") == "en"
    assert normalize_language_code("英文") == "en"


def test_normalize_language_code_none_for_non_string():
    assert normalize_language_code(None) is None
    assert normalize_language_code(123) is None


def test_normalize_language_code_none_for_empty():
    assert normalize_language_code("") is None
    assert normalize_language_code("   ") is None


def test_normalize_language_code_none_for_unknown():
    assert normalize_language_code("fr") is None
    assert normalize_language_code("ja") is None


def test_describe_language_zh():
    assert "中文" in describe_language("zh")
    assert "简体中文" in describe_language("zh")


def test_describe_language_en():
    assert "English" in describe_language("en")


def test_describe_language_unknown_defaults_zh():
    result = describe_language("fr")
    assert "中文" in result


def test_detect_language_with_model_success(monkeypatch):
    async def _fake_post_chat_completion(*, model, messages, tools=None):
        return {"message": {"content": '{"language":"zh","reason":"中文内容"}'}}

    monkeypatch.setattr(
        language_policy_module,
        "post_chat_completion",
        _fake_post_chat_completion,
    )

    lang, reason = asyncio.run(
        detect_language_with_model(model="test", context_text="测试", task_name="test")
    )
    assert lang == "zh"
    assert reason == "中文内容"


def test_detect_language_with_model_api_error(monkeypatch):
    async def _fake_post_chat_completion(*, model, messages, tools=None):
        raise RuntimeError("connection failed")

    monkeypatch.setattr(
        language_policy_module,
        "post_chat_completion",
        _fake_post_chat_completion,
    )

    lang, reason = asyncio.run(
        detect_language_with_model(model="test", context_text="测试", task_name="test")
    )
    assert lang is None
    assert "detect_error" in reason


def test_detect_language_with_model_invalid_json(monkeypatch):
    async def _fake_post_chat_completion(*, model, messages, tools=None):
        return {"message": {"content": "not json"}}

    monkeypatch.setattr(
        language_policy_module,
        "post_chat_completion",
        _fake_post_chat_completion,
    )

    lang, reason = asyncio.run(
        detect_language_with_model(model="test", context_text="测试", task_name="test")
    )
    assert lang is None
    assert reason == "detect_invalid_json"


def test_detect_language_with_model_unknown_language(monkeypatch):
    async def _fake_post_chat_completion(*, model, messages, tools=None):
        return {"message": {"content": '{"language":"fr","reason":"French text"}'}}

    monkeypatch.setattr(
        language_policy_module,
        "post_chat_completion",
        _fake_post_chat_completion,
    )

    lang, reason = asyncio.run(
        detect_language_with_model(model="test", context_text="test", task_name="test")
    )
    assert lang is None
    assert "French" in reason


def test_verify_text_language_with_model_success(monkeypatch):
    async def _fake_post_chat_completion(*, model, messages, tools=None):
        return {
            "message": {
                "content": '{"match":true,"detected_language":"zh","reason":"matches"}'
            }
        }

    monkeypatch.setattr(
        language_policy_module,
        "post_chat_completion",
        _fake_post_chat_completion,
    )

    match, detected, reason = asyncio.run(
        verify_text_language_with_model(
            model="test", expected_language="zh", text="测试文本", task_name="test"
        )
    )
    assert match is True
    assert detected == "zh"
    assert reason == "matches"


def test_verify_text_language_with_model_invalid_expected():
    match, detected, reason = asyncio.run(
        verify_text_language_with_model(
            model="test", expected_language="fr", text="test", task_name="test"
        )
    )
    assert match is None
    assert detected is None
    assert reason == "verify_invalid_expected_language"


def test_verify_text_language_with_model_api_error(monkeypatch):
    async def _fake_post_chat_completion(*, model, messages, tools=None):
        raise RuntimeError("connection failed")

    monkeypatch.setattr(
        language_policy_module,
        "post_chat_completion",
        _fake_post_chat_completion,
    )

    match, detected, reason = asyncio.run(
        verify_text_language_with_model(
            model="test", expected_language="zh", text="测试", task_name="test"
        )
    )
    assert match is None
    assert detected is None
    assert "verify_error" in reason


def test_verify_text_language_with_model_invalid_json(monkeypatch):
    async def _fake_post_chat_completion(*, model, messages, tools=None):
        return {"message": {"content": "not json"}}

    monkeypatch.setattr(
        language_policy_module,
        "post_chat_completion",
        _fake_post_chat_completion,
    )

    match, detected, reason = asyncio.run(
        verify_text_language_with_model(
            model="test", expected_language="zh", text="测试", task_name="test"
        )
    )
    assert match is None
    assert detected is None
    assert reason == "verify_invalid_json"


def test_verify_text_language_with_model_non_bool_match(monkeypatch):
    async def _fake_post_chat_completion(*, model, messages, tools=None):
        return {
            "message": {
                "content": '{"match":"yes","detected_language":"zh","reason":"ok"}'
            }
        }

    monkeypatch.setattr(
        language_policy_module,
        "post_chat_completion",
        _fake_post_chat_completion,
    )

    match, detected, reason = asyncio.run(
        verify_text_language_with_model(
            model="test", expected_language="zh", text="测试", task_name="test"
        )
    )
    assert match is None
    assert detected == "zh"
