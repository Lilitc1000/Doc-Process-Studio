from datetime import UTC, datetime

from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.routers.chat_sessions as chat_sessions_router_module
from doc_process_studio.models.chat_sessions import (
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionSnapshot,
    ChatSessionSummary,
)


def _build_summary(session_id: str, title: str) -> ChatSessionSummary:
    now = datetime.now(UTC)
    return ChatSessionSummary(
        id=session_id,
        title=title,
        created_at=now,
        updated_at=now,
        selected_processing_mode="document-assistant",
        selected_model="qwen2.5:7b",
    )


def _build_snapshot() -> ChatSessionSnapshot:
    return ChatSessionSnapshot(
        message_nodes=[],
        root_child_ids=[],
        selected_root_child_id=None,
        selected_child_id_by_parent={},
        selected_processing_mode="document-assistant",
        selected_model="qwen2.5:7b",
    )


def test_api_chat_sessions_list_returns_summaries(monkeypatch) -> None:
    async def fake_list_chat_sessions() -> ChatSessionListResponse:
        return ChatSessionListResponse(
            sessions=[_build_summary("conversation-1", "第一条会话")]
        )

    monkeypatch.setattr(
        chat_sessions_router_module,
        "list_chat_sessions",
        fake_list_chat_sessions,
    )

    client = TestClient(main_module.app)
    response = client.get("/api/chat-sessions")

    assert response.status_code == 200
    assert response.json()["sessions"][0]["id"] == "conversation-1"


def test_api_chat_sessions_get_returns_detail(monkeypatch) -> None:
    async def fake_get_chat_session(session_id: str) -> ChatSessionDetail:
        assert session_id == "conversation-1"
        summary = _build_summary(session_id, "第一条会话")
        return ChatSessionDetail(
            **summary.model_dump(),
            snapshot=_build_snapshot(),
        )

    monkeypatch.setattr(
        chat_sessions_router_module,
        "get_chat_session",
        fake_get_chat_session,
    )

    client = TestClient(main_module.app)
    response = client.get("/api/chat-sessions/conversation-1")

    assert response.status_code == 200
    assert response.json()["title"] == "第一条会话"


def test_api_chat_sessions_save_upserts_snapshot(monkeypatch) -> None:
    async def fake_upsert_chat_session(**kwargs) -> ChatSessionSummary:
        assert kwargs["session_id"] == "conversation-1"
        assert kwargs["title_source_messages"] == ["你好", "请总结文档"]
        return _build_summary("conversation-1", "文档总结")

    monkeypatch.setattr(
        chat_sessions_router_module,
        "upsert_chat_session",
        fake_upsert_chat_session,
    )

    client = TestClient(main_module.app)
    response = client.put(
        "/api/chat-sessions/conversation-1",
        json={
            "title": "",
            "title_source_messages": ["你好", "请总结文档"],
            "snapshot": _build_snapshot().model_dump(mode="json"),
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "文档总结"


def test_api_chat_sessions_delete_clears_state(monkeypatch) -> None:
    async def fake_delete_chat_session(session_id: str) -> bool:
        assert session_id == "conversation-1"
        return True

    async def fake_clear_conversation_state(conversation_id: str) -> bool:
        assert conversation_id == "conversation-1"
        return True

    monkeypatch.setattr(
        chat_sessions_router_module,
        "delete_chat_session",
        fake_delete_chat_session,
    )
    monkeypatch.setattr(
        chat_sessions_router_module,
        "clear_conversation_state",
        fake_clear_conversation_state,
    )

    client = TestClient(main_module.app)
    response = client.delete("/api/chat-sessions/conversation-1")

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
