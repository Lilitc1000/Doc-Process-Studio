from datetime import UTC, datetime

from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
from doc_process_studio.chat.application.contracts import SessionServiceContract
from doc_process_studio.chat.application.dtos.session import (
    ChatSessionSnapshot,
    ChatSessionSummary,
)
from doc_process_studio.chat.infrastructure.dependencies import get_session_service
from doc_process_studio.chat.router.schemas.response import (
    ChatSessionDetail,
    ChatSessionListResponse,
)


def _build_summary(session_id: str, title: str) -> ChatSessionSummary:
    now = datetime.now(UTC)
    return ChatSessionSummary(
        id=session_id,
        title=title,
        created_at=now,
        updated_at=now,
        selected_model="qwen2.5:7b",
    )


def _build_snapshot() -> ChatSessionSnapshot:
    return ChatSessionSnapshot(
        message_nodes=[],
        root_child_ids=[],
        selected_root_child_id=None,
        selected_child_id_by_parent={},
        selected_model="qwen2.5:7b",
    )


class _FakeSessionService(SessionServiceContract):
    """测试用 SessionService 桩，绕过真实端口依赖。"""

    async def list_sessions(self, user_id: str) -> ChatSessionListResponse:
        _ = user_id
        return ChatSessionListResponse(sessions=[_build_summary("conversation-1", "第一条会话")])

    async def get_session(self, session_id: str, user_id: str) -> ChatSessionDetail:
        _ = user_id
        assert session_id == "conversation-1"
        summary = _build_summary(session_id, "第一条会话")
        return ChatSessionDetail(
            **summary.model_dump(),
            snapshot=_build_snapshot(),
        )

    async def save_session(
        self,
        *,
        session_id: str,
        user_id: str,
        title: str,
        title_source_messages: list[str],
        snapshot: ChatSessionSnapshot,
    ) -> ChatSessionSummary:
        _ = (user_id, title, title_source_messages, snapshot)
        assert session_id == "conversation-1"
        return _build_summary("conversation-1", "文档总结")

    async def rename_session(self, session_id: str, user_id: str, title: str) -> ChatSessionSummary:
        _ = (session_id, user_id, title)
        raise NotImplementedError

    async def delete_sessions_by_title_prefix(self, user_id: str, title_prefix: str) -> int:
        _ = (user_id, title_prefix)
        raise NotImplementedError

    async def delete_sessions_by_user(self, target_user_id: str, user_id: str) -> int:
        _ = (target_user_id, user_id)
        raise NotImplementedError

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        _ = user_id
        assert session_id == "conversation-1"
        return True


def _install_fake_service(monkeypatch, fake: _FakeSessionService) -> None:
    monkeypatch.setitem(
        main_module.app.dependency_overrides,
        get_session_service,
        lambda: fake,
    )


def test_api_chat_sessions_list_returns_summaries(monkeypatch, auth_headers) -> None:
    _install_fake_service(monkeypatch, _FakeSessionService())

    client = TestClient(main_module.app)
    response = client.get("/api/chat-sessions", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["sessions"][0]["id"] == "conversation-1"


def test_api_chat_sessions_get_returns_detail(monkeypatch, auth_headers) -> None:
    _install_fake_service(monkeypatch, _FakeSessionService())

    client = TestClient(main_module.app)
    response = client.get("/api/chat-sessions/conversation-1", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["title"] == "第一条会话"


def test_api_chat_sessions_save_upserts_snapshot(monkeypatch, auth_headers) -> None:
    _install_fake_service(monkeypatch, _FakeSessionService())

    client = TestClient(main_module.app)
    response = client.put(
        "/api/chat-sessions/conversation-1",
        json={
            "title": "",
            "title_source_messages": ["你好", "请总结文档"],
            "snapshot": _build_snapshot().model_dump(mode="json"),
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "文档总结"


def test_api_chat_sessions_delete_clears_state(monkeypatch, auth_headers) -> None:
    _install_fake_service(monkeypatch, _FakeSessionService())

    client = TestClient(main_module.app)
    response = client.delete("/api/chat-sessions/conversation-1", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
