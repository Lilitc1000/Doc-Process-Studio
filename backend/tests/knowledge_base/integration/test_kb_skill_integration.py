"""
集成测试：验证 kb: skill 在 skill 解析和上下文构建阶段不会抛出 ValueError。

直接调用 stream_remote_chat_completion，验证 kb: skill 在整个链路中的错误处理。
此测试不需要 Ollama 服务可用，重点验证 skill 解析和上下文构建阶段。
"""

import json

from doc_process_studio.chat.infrastructure.stream import stream_remote_chat_completion
from doc_process_studio.chat.router.schemas.request import ChatMessageInput, ChatStreamRequest
from doc_process_studio.skill.infrastructure.context import load_skill_context_chunks


def _make_request(skill_ids: list[str]) -> ChatStreamRequest:
    return ChatStreamRequest(
        user_message_id="msg-e2e-001",
        conversation_id="conv-e2e-001",
        model="test-model",
        messages=[ChatMessageInput(role="user", content="你好")],
        selected_skill_ids=skill_ids,
    )


async def _collect_stream_events(request: ChatStreamRequest) -> list[dict]:
    """收集流式事件，直到遇到 error 或 done 事件。"""
    events = []
    async for raw_sse in stream_remote_chat_completion(request):
        for line in raw_sse.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                try:
                    event = json.loads(line[6:])
                    events.append(event)
                    if event.get("type") == "error" or event.get("done") is True:
                        return events
                except json.JSONDecodeError:
                    pass
    return events


def _get_first_error_message(events: list[dict]) -> str:
    """获取第一个 error 事件的消息。"""
    for e in events:
        if e.get("type") == "error":
            return e.get("message", "")
    return ""


# ── 核心断言：kb: skill 不应触发 "未找到 skill" ValueError ──


async def test_kb_skill_only_no_ollama() -> None:
    """选择 kb: skill 但无 Ollama 服务时，应返回 Ollama 连接错误而非 ValueError。"""
    load_skill_context_chunks.cache_clear()
    request = _make_request(["kb:TestProject"])
    events = await _collect_stream_events(request)

    error_msg = _get_first_error_message(events)
    if error_msg:
        assert "未找到 skill" not in error_msg, (
            f"kb: skill 不应触发 get_skill_interface ValueError，实际错误: {error_msg}"
        )


async def test_kb_skill_mixed_with_regular_no_ollama() -> None:
    """kb: skill 与普通 skill 混合选择时，不应抛出 ValueError。"""
    load_skill_context_chunks.cache_clear()
    request = _make_request(["document-assistant", "kb:出租车平台"])
    events = await _collect_stream_events(request)

    error_msg = _get_first_error_message(events)
    if error_msg:
        assert "未找到 skill" not in error_msg, (
            f"混合 skill 不应触发 get_skill_interface ValueError，实际错误: {error_msg}"
        )


async def test_kb_skill_chinese_name_no_ollama() -> None:
    """中文项目名的 kb: skill 不应抛出 ValueError。"""
    load_skill_context_chunks.cache_clear()
    request = _make_request(["kb:出租车平台"])
    events = await _collect_stream_events(request)

    error_msg = _get_first_error_message(events)
    if error_msg:
        assert "未找到 skill" not in error_msg, f"中文 kb: skill 不应触发 ValueError，实际错误: {error_msg}"


async def test_kb_skill_trace_id_returned() -> None:
    """kb: skill 请求应正常返回 trace_id。"""
    load_skill_context_chunks.cache_clear()
    request = _make_request(["kb:TestProject"])
    events = await _collect_stream_events(request)

    trace_events = [e for e in events if e.get("type") == "trace" and e.get("phase") == "start"]
    assert len(trace_events) >= 1, "应至少返回一个 trace start 事件"
    trace_event = trace_events[0]
    assert "traceId" in trace_event or "trace_id" in trace_event, f"trace 事件应包含 traceId，实际: {trace_event}"


async def test_multiple_kb_skills_no_ollama() -> None:
    """多个 kb: skill 同时选择不应抛出 ValueError。"""
    load_skill_context_chunks.cache_clear()
    request = _make_request(["kb:ProjectA", "kb:ProjectB"])
    events = await _collect_stream_events(request)

    error_msg = _get_first_error_message(events)
    if error_msg:
        assert "未找到 skill" not in error_msg, f"多个 kb: skill 不应触发 ValueError，实际错误: {error_msg}"


async def test_kb_skill_with_special_chars_no_ollama() -> None:
    """包含特殊字符的项目名不应导致异常。"""
    load_skill_context_chunks.cache_clear()
    request = _make_request(["kb:Project-Test_123"])
    events = await _collect_stream_events(request)

    error_msg = _get_first_error_message(events)
    if error_msg:
        assert "未找到 skill" not in error_msg, f"特殊字符 kb: skill 不应触发 ValueError，实际错误: {error_msg}"


async def test_kb_skill_error_is_ollama_related_not_skill_related() -> None:
    """kb: skill 的错误应与 Ollama 连接相关，而非 skill 查找相关。"""
    load_skill_context_chunks.cache_clear()
    request = _make_request(["kb:出租车平台"])
    events = await _collect_stream_events(request)

    error_msg = _get_first_error_message(events)
    if error_msg:
        is_ollama_error = any(
            kw in error_msg for kw in ["Ollama", "ollama", "连接", "远程", "OLLAMA_BASE_URL", "HTTP", "404"]
        )
        is_skill_error = "未找到 skill" in error_msg
        assert is_ollama_error or not is_skill_error, (
            f"错误应与 Ollama 连接相关，而非 skill 查找。实际错误: {error_msg}"
        )


def test_load_skill_context_chunks_returns_empty_for_kb_skill() -> None:
    """load_skill_context_chunks 对 kb: skill 应返回空列表。"""
    load_skill_context_chunks.cache_clear()
    result = load_skill_context_chunks("kb:TestProject")
    assert result == [], f"kb: skill 应返回空列表，实际: {result}"


def test_load_skill_context_chunks_returns_empty_for_kb_chinese() -> None:
    """load_skill_context_chunks 对中文 kb: skill 应返回空列表。"""
    load_skill_context_chunks.cache_clear()
    result = load_skill_context_chunks("kb:出租车平台")
    assert result == [], f"中文 kb: skill 应返回空列表，实际: {result}"
