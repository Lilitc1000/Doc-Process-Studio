"""
E2E 测试：通过 HTTP 调用 /api/chat/stream 模拟知识库对话。

此测试需要后端服务运行在 http://localhost:8000，且 Ollama 可用。
测试流程：
1. 登录获取 JWT token
2. 查询可用的知识库项目
3. 选择 kb: skill 发起对话
4. 验证 AI 能根据知识库内容回答问题

SSE 事件格式说明：
- trace 事件: {"type": "trace", "phase": "start", "trace_id": "..."}
- tool-status 事件: {"type": "tool-status", "phase": "start|finish", "tool_name": "...", ...}
- 内容事件: {"model": "...", "message": {"role": "assistant", "content": "..."}, "done": false}
- 完成事件: {"model": "...", "message": {"role": "assistant", "content": ""}, "done": true, "done_reason": "stop"}
- 错误事件: {"type": "error", "message": "..."}
"""

import json
import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# 模块级缓存，避免重复登录触发限流
_cached_token: str | None = None
_cached_projects: list[dict] | None = None
_cached_models: list[str] | None = None


def _get_auth_token() -> str:
    global _cached_token
    if _cached_token:
        return _cached_token
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        )
        resp.raise_for_status()
        _cached_token = resp.json()["access_token"]
        return _cached_token


def _get_kb_projects(token: str) -> list[dict]:
    global _cached_projects
    if _cached_projects is not None:
        return _cached_projects
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            f"{BASE_URL}/api/knowledge-base/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        _cached_projects = resp.json()["projects"]
        return _cached_projects


def _get_models(token: str) -> list[str]:
    global _cached_models
    if _cached_models is not None:
        return _cached_models
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            f"{BASE_URL}/api/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        _cached_models = [m["name"] for m in resp.json()["models"]]
        return _cached_models


def _select_chat_model(models: list[str]) -> str:
    """从可用模型中选择一个适合对话的模型。"""
    preferred = ["qwen3.6:35b", "qwen3.6:35b-mlx", "gemma4:31b", "llama3.3:70b"]
    for model in preferred:
        if model in models:
            return model
    for model in models:
        if "embed" not in model.lower() and "rerank" not in model.lower() and "bge" not in model.lower():
            return model
    return models[0] if models else "unknown"


def _is_content_event(event: dict) -> bool:
    """判断事件是否为 AI 内容事件（包含 message 且 done 为 false）。"""
    return "message" in event and event.get("done") is False


def _is_done_event(event: dict) -> bool:
    """判断事件是否为对话完成事件。"""
    return event.get("done") is True


def _collect_assistant_content(events: list[dict]) -> str:
    """从内容事件中提取完整的 AI 回复文本。"""
    parts: list[str] = []
    for e in events:
        if _is_content_event(e):
            msg = e.get("message", {})
            content = msg.get("content", "")
            if content:
                parts.append(content)
    return "".join(parts)


def _stream_chat(token: str, payload: dict, timeout: float = 180) -> list[dict]:
    """调用 /api/chat/stream 并收集所有 SSE 事件。"""
    events: list[dict] = []
    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "POST",
            f"{BASE_URL}/api/chat/stream",
            headers={"Authorization": f"Bearer {token}"},
            data={"payload": json.dumps(payload, ensure_ascii=False)},
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                    events.append(event)
                except json.JSONDecodeError:
                    pass
    return events


def _check_backend_available() -> bool:
    """检查后端是否可用。"""
    try:
        _get_auth_token()
        return True
    except Exception:
        return False


backend_available = _check_backend_available()


# ── 测试用例 ──


@pytest.mark.skipif(not backend_available, reason="Backend not running or auth failed")
def test_kb_skill_chat_returns_trace_and_content() -> None:
    """kb: skill 对话应返回 trace 事件和 AI 内容。"""
    token = _get_auth_token()
    projects = _get_kb_projects(token)
    if not projects:
        pytest.skip("No knowledge base projects available")

    project_name = projects[0]["name"]
    models = _get_models(token)
    model = _select_chat_model(models)

    payload = {
        "user_message_id": f"msg-e2e-{uuid.uuid4().hex[:8]}",
        "conversation_id": f"conv-e2e-{uuid.uuid4().hex[:8]}",
        "model": model,
        "selected_skill_ids": [f"kb:{project_name}"],
        "messages": [{"role": "user", "content": f"请简单介绍一下{project_name}的核心功能"}],
    }

    events = _stream_chat(token, payload, timeout=180)

    # 验证 trace 事件
    trace_events = [e for e in events if e.get("type") == "trace" and e.get("phase") == "start"]
    assert len(trace_events) >= 1, "应至少返回一个 trace start 事件"

    # 验证没有 "未找到 skill" 错误
    error_events = [e for e in events if e.get("type") == "error"]
    for err in error_events:
        assert "未找到 skill" not in err.get("message", ""), (
            f"kb: skill 不应触发 ValueError: {err['message']}"
        )

    # 验证有 AI 内容返回（内容事件格式为 {"message": {...}, "done": false}）
    content_events = [e for e in events if _is_content_event(e)]
    assert len(content_events) >= 1, (
        f"应返回 AI 内容事件，实际事件: {[list(e.keys()) for e in events[:5]]}"
    )

    # 验证有 done 事件
    done_events = [e for e in events if _is_done_event(e)]
    assert len(done_events) >= 1, "应返回 done 事件"


@pytest.mark.skipif(not backend_available, reason="Backend not running or auth failed")
def test_kb_skill_chat_completes_without_connection_error() -> None:
    """kb: skill 对话应正常完成，不应因连接断开而中断。"""
    token = _get_auth_token()
    projects = _get_kb_projects(token)
    if not projects:
        pytest.skip("No knowledge base projects available")

    project_name = projects[0]["name"]
    models = _get_models(token)
    model = _select_chat_model(models)

    payload = {
        "user_message_id": f"msg-e2e-{uuid.uuid4().hex[:8]}",
        "conversation_id": f"conv-e2e-{uuid.uuid4().hex[:8]}",
        "model": model,
        "selected_skill_ids": [f"kb:{project_name}"],
        "messages": [{"role": "user", "content": "你好"}],
    }

    # _stream_chat 应能正常收集所有事件而不抛出 RemoteProtocolError
    events = _stream_chat(token, payload, timeout=180)

    # 应该有 done 或 error 事件，不能什么都没有就断开
    done_events = [e for e in events if _is_done_event(e)]
    error_events = [e for e in events if e.get("type") == "error"]
    assert len(done_events) >= 1 or len(error_events) >= 1, (
        "对话应正常结束（done）或返回错误事件（error），不应直接断开连接"
    )


@pytest.mark.skipif(not backend_available, reason="Backend not running or auth failed")
def test_kb_skill_chat_invokes_search_tool() -> None:
    """kb: skill 对话应调用 search_knowledge_base 工具进行 RAG 检索。"""
    token = _get_auth_token()
    projects = _get_kb_projects(token)
    if not projects:
        pytest.skip("No knowledge base projects available")

    project_name = projects[0]["name"]
    models = _get_models(token)
    model = _select_chat_model(models)

    payload = {
        "user_message_id": f"msg-e2e-{uuid.uuid4().hex[:8]}",
        "conversation_id": f"conv-e2e-{uuid.uuid4().hex[:8]}",
        "model": model,
        "selected_skill_ids": [f"kb:{project_name}"],
        "messages": [{"role": "user", "content": f"请根据知识库内容，告诉我{project_name}有哪些功能"}],
    }

    events = _stream_chat(token, payload, timeout=180)

    # 对话应正常完成
    done_events = [e for e in events if _is_done_event(e)]
    assert len(done_events) >= 1, "对话应正常完成"

    # 检查是否有 search_knowledge_base 工具状态事件
    tool_status_events = [
        e for e in events
        if e.get("type") == "tool-status" and e.get("tool_name") == "search_knowledge_base"
    ]
    assert len(tool_status_events) >= 1, (
        f"kb: skill 对话应调用 search_knowledge_base 工具，"
        f"实际工具事件: {[e.get('tool_name') for e in events if e.get('type') == 'tool-status']}"
    )

    # 验证工具至少有一个 start 事件
    tool_start_events = [e for e in tool_status_events if e.get("phase") == "start"]
    assert len(tool_start_events) >= 1, "search_knowledge_base 工具应有 start 阶段"


@pytest.mark.skipif(not backend_available, reason="Backend not running or auth failed")
def test_kb_skill_chat_assistant_reply_is_nonempty() -> None:
    """kb: skill 对话中 AI 应返回非空的回复内容。"""
    token = _get_auth_token()
    projects = _get_kb_projects(token)
    if not projects:
        pytest.skip("No knowledge base projects available")

    project_name = projects[0]["name"]
    models = _get_models(token)
    model = _select_chat_model(models)

    payload = {
        "user_message_id": f"msg-e2e-{uuid.uuid4().hex[:8]}",
        "conversation_id": f"conv-e2e-{uuid.uuid4().hex[:8]}",
        "model": model,
        "selected_skill_ids": [f"kb:{project_name}"],
        "messages": [{"role": "user", "content": f"请简单介绍一下{project_name}"}],
    }

    events = _stream_chat(token, payload, timeout=180)

    # 提取完整回复
    full_reply = _collect_assistant_content(events)
    assert len(full_reply.strip()) > 0, "AI 回复不应为空"

    # 验证 done_reason 为 stop（正常结束）
    done_events = [e for e in events if _is_done_event(e)]
    if done_events:
        assert done_events[-1].get("done_reason") == "stop", (
            f"对话应正常结束（done_reason=stop），实际: {done_events[-1].get('done_reason')}"
        )
