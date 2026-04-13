from doc_process_studio.services.infra import model_context as model_context_module


def test_estimate_prompt_tokens_returns_positive_value() -> None:
    tokens = model_context_module.estimate_prompt_tokens(
        [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": "请总结这份报告"},
        ]
    )
    assert isinstance(tokens, int)
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

