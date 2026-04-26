import asyncio

from doc_process_studio.core import model_context as model_context_module


def test_estimate_prompt_tokens_returns_positive_value() -> None:
    tokens = model_context_module.estimate_prompt_tokens(
        [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": "请总结这份报告"},
        ]
    )
    assert isinstance(tokens, int)
    assert tokens > 0


def test_estimate_prompt_tokens_empty_messages() -> None:
    assert model_context_module.estimate_prompt_tokens([]) == 0


def test_estimate_prompt_tokens_with_tool_calls() -> None:
    tokens = model_context_module.estimate_prompt_tokens(
        [
            {
                "role": "assistant",
                "content": "使用工具",
                "tool_calls": [{"function": {"name": "search", "arguments": "{}"}}],
            }
        ]
    )
    assert tokens > 0


def test_estimate_prompt_tokens_missing_fields() -> None:
    tokens = model_context_module.estimate_prompt_tokens([{}])
    assert tokens > 0


def test_extract_context_length_supports_multiple_payload_shapes() -> None:
    payload_a = {"context_length": 16384}
    payload_b = {"details": {"num_ctx": 32768}}
    payload_c = {"model_info": {"llama.context_length": 8192}}
    payload_d = {"parameters": "num_ctx 4096"}

    assert model_context_module._extract_context_length(payload_a) == 16384
    assert model_context_module._extract_context_length(payload_b) == 32768
    assert model_context_module._extract_context_length(payload_c) == 8192
    assert model_context_module._extract_context_length(payload_d) == 4096


def test_extract_int_like_bool_returns_none() -> None:
    assert model_context_module._extract_int_like(True) is None
    assert model_context_module._extract_int_like(False) is None


def test_extract_int_like_int() -> None:
    assert model_context_module._extract_int_like(8192) == 8192
    assert model_context_module._extract_int_like(0) is None
    assert model_context_module._extract_int_like(-1) is None


def test_extract_int_like_float() -> None:
    assert model_context_module._extract_int_like(8192.0) == 8192
    assert model_context_module._extract_int_like(0.0) is None


def test_extract_int_like_string() -> None:
    assert model_context_module._extract_int_like("8192") == 8192
    assert model_context_module._extract_int_like("abc") is None
    assert model_context_module._extract_int_like("12") is None


def test_extract_int_like_none() -> None:
    assert model_context_module._extract_int_like(None) is None


def test_extract_context_length_returns_none_for_empty() -> None:
    assert model_context_module._extract_context_length({}) is None


def test_extract_context_length_num_ctx_train() -> None:
    assert model_context_module._extract_context_length({"num_ctx_train": 4096}) == 4096


def test_extract_context_length_parameters_with_context_length() -> None:
    assert model_context_module._extract_context_length(
        {"parameters": "context_length=8192"}
    ) == 8192


def test_extract_context_length_model_info_with_ctx() -> None:
    assert model_context_module._extract_context_length(
        {"model_info": {"some.ctx.field": 16384}}
    ) == 16384


def test_is_cache_fresh_within_ttl() -> None:
    from datetime import UTC, datetime

    cached_at = datetime.now(UTC)
    assert model_context_module._is_cache_fresh(cached_at) is True


def test_is_cache_fresh_expired() -> None:
    from datetime import UTC, datetime, timedelta

    cached_at = datetime.now(UTC) - timedelta(days=365)
    assert model_context_module._is_cache_fresh(cached_at) is False


def test_get_model_context_length_empty_model() -> None:
    result = asyncio.run(model_context_module.get_model_context_length(""))
    assert result == model_context_module.settings.agent_executor_default_context_length


def test_set_cached_context_length() -> None:
    from datetime import datetime

    model_context_module._CONTEXT_CACHE.clear()
    asyncio.run(model_context_module._set_cached_context_length("test-model", 8192))
    assert "test-model" in model_context_module._CONTEXT_CACHE
    cached_length, cached_at = model_context_module._CONTEXT_CACHE["test-model"]
    assert cached_length == 8192
    assert isinstance(cached_at, datetime)
    model_context_module._CONTEXT_CACHE.clear()


def test_warmup_model_context_cache_skips_when_no_base_url(monkeypatch) -> None:
    model_context_module._WARMED_UP = False
    monkeypatch.setattr(model_context_module.settings, "ollama_base_url", None)
    asyncio.run(model_context_module.warmup_model_context_cache())
    assert model_context_module._WARMED_UP is True
    model_context_module._WARMED_UP = False


def test_warmup_model_context_cache_skips_when_already_warmed() -> None:
    model_context_module._WARMED_UP = True
    asyncio.run(model_context_module.warmup_model_context_cache())
    model_context_module._WARMED_UP = False


def test_fetch_model_context_length_empty_model() -> None:
    result = asyncio.run(model_context_module._fetch_model_context_length(""))
    assert result is None


def test_get_model_context_length_with_fresh_cache() -> None:
    from datetime import UTC, datetime

    model_context_module._CONTEXT_CACHE.clear()
    model_context_module._CONTEXT_CACHE["cached-model"] = (
        8192,
        datetime.now(UTC),
    )
    result = asyncio.run(model_context_module.get_model_context_length("cached-model"))
    assert result == 8192
    model_context_module._CONTEXT_CACHE.clear()

