from doc_process_studio.chat.schemas.request import (
    ChatMessageInput,
    ChatStreamRequest,
)
from doc_process_studio.chat.service.streaming import (
    build_skill_prompt,
    build_upstream_messages_for_skills,
    extract_delta_text,
    extract_done_reason,
    merge_stream_tool_calls,
)


def test_extract_delta_text_reads_ollama_native_chunk() -> None:
    payload = {
        "model": "qwen3-coder-next:latest",
        "message": {
            "role": "assistant",
            "content": "你好，",
        },
        "done": False,
    }

    assert extract_delta_text(payload) == "你好，"


def test_extract_done_reason_reads_done_signal() -> None:
    payload = {
        "model": "qwen3-coder-next:latest",
        "message": {"role": "assistant", "content": ""},
        "done": True,
        "done_reason": "stop",
    }

    assert extract_done_reason(payload) == "stop"


def test_build_skill_prompt_returns_skill_default_prompt() -> None:
    prompt = build_skill_prompt("document-assistant")

    assert "$document-assistant" in prompt


def test_build_upstream_messages_for_skills_prepends_system_prompt() -> None:
    request = ChatStreamRequest(
        user_message_id="user-1",
        conversation_id="conversation-1",
        model="qwen2.5:7b",
        skill_id="document-assistant",
        messages=[
            ChatMessageInput(role="user", content="请解释这份文档"),
        ],
        attachment_ids=[],
    )

    upstream_messages = build_upstream_messages_for_skills(
        request=request,
        active_skill_ids=["document-assistant"],
        explicit_skill_ids=["document-assistant"],
    )

    assert upstream_messages[0]["role"] == "system"
    assert "$document-assistant" in upstream_messages[0]["content"]
    assert upstream_messages[1]["role"] == "system"
    assert "渐进式披露" in upstream_messages[1]["content"]
    assert upstream_messages[2] == {
        "role": "user",
        "content": "请解释这份文档",
    }


def test_merge_stream_tool_calls_splits_reused_index_complete_calls() -> None:
    merged: dict[int, dict] = {}
    merge_stream_tool_calls(
        merged,
        [
            {
                "index": 0,
                "type": "function",
                "function": {
                    "name": "list_skill_directory",
                    "arguments": {"relative_path": "."},
                },
            }
        ],
    )
    merge_stream_tool_calls(
        merged,
        [
            {
                "index": 0,
                "type": "function",
                "function": {
                    "name": "list_skill_directory",
                    "arguments": {"relative_path": "references"},
                },
            }
        ],
    )

    assert len(merged) == 2
    assert merged[0]["function"]["name"] == "list_skill_directory"
    assert merged[1]["function"]["name"] == "list_skill_directory"
    assert '"relative_path": "."' in merged[0]["function"]["arguments"]
    assert '"relative_path": "references"' in merged[1]["function"]["arguments"]


def test_merge_stream_tool_calls_keeps_progressive_single_call() -> None:
    merged: dict[int, dict] = {}
    merge_stream_tool_calls(
        merged,
        [
            {
                "index": 0,
                "type": "function",
                "function": {
                    "name": "generate_document",
                    "arguments": {},
                },
            }
        ],
    )
    merge_stream_tool_calls(
        merged,
        [
            {
                "index": 0,
                "type": "function",
                "function": {
                    "name": "generate_document",
                    "arguments": {"system_name": "交通系统"},
                },
            }
        ],
    )

    assert len(merged) == 1
    assert merged[0]["function"]["name"] == "generate_document"
    assert '"system_name": "交通系统"' in merged[0]["function"]["arguments"]
