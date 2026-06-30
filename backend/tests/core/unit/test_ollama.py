from typing import Any

import httpx
import pytest

import doc_process_studio.common.infrastructure.ollama as ollama_module
from doc_process_studio.common.infrastructure.exceptions import OllamaNotConfiguredError
from doc_process_studio.common.infrastructure.ollama import (
    build_chat_payload,
    build_timeout,
    extract_first_message_content,
    extract_model_names,
    get_ollama_base_url,
)


def test_get_ollama_base_url_raises_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ollama_module.settings, "ollama_base_url", None)
    with pytest.raises(OllamaNotConfiguredError):
        get_ollama_base_url()


def test_get_ollama_base_url_returns_stripped_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ollama_module.settings, "ollama_base_url", "http://ollama:11434/")
    assert get_ollama_base_url() == "http://ollama:11434"


def test_build_timeout_default() -> None:
    timeout = build_timeout()
    assert isinstance(timeout, httpx.Timeout)


def test_build_timeout_stream() -> None:
    timeout = build_timeout(stream=True)
    assert isinstance(timeout, httpx.Timeout)


def test_build_chat_payload_plain_messages() -> None:
    messages = [{"role": "user", "content": "hello"}]
    payload = build_chat_payload(model="test-model", messages=messages, stream=False)
    assert payload["model"] == "test-model"
    assert payload["stream"] is False
    assert payload["messages"] == messages
    assert "tools" not in payload


def test_build_chat_payload_with_tools() -> None:
    messages = [{"role": "user", "content": "hello"}]
    tools = [{"type": "function", "function": {"name": "test_tool"}}]
    payload = build_chat_payload(model="test-model", messages=messages, stream=True, tools=tools)
    assert payload["stream"] is True
    assert payload["tools"] == tools


def test_build_chat_payload_normalizes_pydantic_messages() -> None:
    class FakeModel:
        def model_dump(self) -> dict[str, Any]:
            return {"role": "user", "content": "from_pydantic"}

    messages = [FakeModel()]
    payload = build_chat_payload(model="test", messages=messages, stream=False)
    assert payload["messages"] == [{"role": "user", "content": "from_pydantic"}]


def test_extract_first_message_content_with_dict_message() -> None:
    payload = {"message": {"content": "  hello world  "}}
    assert extract_first_message_content(payload) == "hello world"


def test_extract_first_message_content_with_non_dict_message() -> None:
    assert extract_first_message_content({"message": "string"}) == ""


def test_extract_first_message_content_with_non_string_content() -> None:
    assert extract_first_message_content({"message": {"content": 123}}) == ""


def test_extract_first_message_content_with_missing_message() -> None:
    assert extract_first_message_content({}) == ""


def test_extract_model_names_from_models_key() -> None:
    payload = {"models": [{"name": "qwen3:8b"}, {"model": "llama3:70b"}]}
    result = extract_model_names(payload)
    assert "qwen3:8b" in result
    assert "llama3:70b" in result


def test_extract_model_names_from_data_key() -> None:
    payload = {"data": [{"id": "model-a"}, {"name": "model-b"}]}
    result = extract_model_names(payload)
    assert "model-a" in result
    assert "model-b" in result


def test_extract_model_names_from_list() -> None:
    payload = [{"name": "model-1"}, {"model": "model-2"}]
    result = extract_model_names(payload)
    assert "model-1" in result
    assert "model-2" in result


def test_extract_model_names_empty_payload() -> None:
    assert extract_model_names({}) == []
    assert extract_model_names({"models": []}) == []


def test_extract_model_names_dedup() -> None:
    payload = {"models": [{"name": "qwen3:8b"}, {"name": "qwen3:8b"}]}
    result = extract_model_names(payload)
    assert result == ["qwen3:8b"]


def test_extract_model_names_skips_non_dict() -> None:
    payload = {"models": [{"name": "valid"}, "invalid", 123]}
    result = extract_model_names(payload)
    assert result == ["valid"]


def test_extract_model_names_skips_empty_names() -> None:
    payload = {"models": [{"name": ""}, {"name": "   "}, {"name": "valid"}]}
    result = extract_model_names(payload)
    assert result == ["valid"]


async def test_post_chat_completion_success(monkeypatch: pytest.MonkeyPatch) -> Any:
    fake_response = {"message": {"content": "hi"}}

    async def _fake_post_chat_completion(**_kwargs: Any) -> Any:
        return fake_response

    monkeypatch.setattr(ollama_module, "post_chat_completion", _fake_post_chat_completion)

    result = await ollama_module.post_chat_completion(model="test", messages=[{"role": "user", "content": "hi"}])
    assert result["message"]["content"] == "hi"


async def test_fetch_remote_model_names_raises_500_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr(ollama_module.settings, "ollama_base_url", None)
    with pytest.raises(HTTPException) as exc_info:
        await ollama_module.fetch_remote_model_names()
    assert exc_info.value.status_code == 500


async def test_fetch_remote_model_names_raises_502_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr(ollama_module.settings, "ollama_base_url", "http://ollama:11434")

    async def _fake_get(_self: Any, _url: Any) -> None:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)

    with pytest.raises(HTTPException) as exc_info:
        await ollama_module.fetch_remote_model_names()
    assert exc_info.value.status_code == 502


async def test_fetch_remote_model_names_raises_502_on_empty_models(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr(ollama_module.settings, "ollama_base_url", "http://ollama:11434")

    async def _fake_fetch() -> None:
        raise HTTPException(status_code=502, detail="远程 Ollama 未返回可用模型名称")

    monkeypatch.setattr(ollama_module, "fetch_remote_model_names", _fake_fetch)

    with pytest.raises(HTTPException) as exc_info:
        await ollama_module.fetch_remote_model_names()
    assert exc_info.value.status_code == 502
