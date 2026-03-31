from doc_process_studio.services.ollama_chat import (
    build_processing_mode_prompt,
    build_upstream_messages,
    extract_delta_text,
    extract_finish_reason,
)
from doc_process_studio.models.chat import ChatMessageInput, ChatStreamRequest


def test_extract_delta_text_reads_openai_compatible_chunk() -> None:
    payload = {
        "choices": [
            {
                "delta": {
                    "role": "assistant",
                    "content": "你好，",
                },
                "finish_reason": None,
            }
        ]
    }

    assert extract_delta_text(payload) == "你好，"


def test_extract_finish_reason_reads_done_signal() -> None:
    payload = {
        "choices": [
            {
                "delta": {},
                "finish_reason": "stop",
            }
        ]
    }

    assert extract_finish_reason(payload) == "stop"


def test_build_processing_mode_prompt_returns_mode_specific_prompt() -> None:
    prompt = build_processing_mode_prompt("结构化提取")

    assert "结构化信息" in prompt


def test_build_upstream_messages_prepends_processing_mode_system_prompt() -> None:
    request = ChatStreamRequest(
      model="qwen2.5:7b",
      processing_mode="智能问答",
      messages=[
          ChatMessageInput(role="user", content="请解释这份文档"),
      ],
    )

    upstream_messages = build_upstream_messages(request)

    assert upstream_messages[0]["role"] == "system"
    assert "围绕用户问题直接作答" in upstream_messages[0]["content"]
    assert upstream_messages[1] == {
        "role": "user",
        "content": "请解释这份文档",
    }
