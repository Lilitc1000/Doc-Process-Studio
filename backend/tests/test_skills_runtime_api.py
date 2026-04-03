from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.routers.skills as skills_router_module
from doc_process_studio.models.skill_runtime import (
    SkillContextChunk,
    SkillConversationState,
)
from doc_process_studio.services.skill_runtime import (
    _build_local_compact_summary,
    _build_skill_context_budget_text,
)


def test_api_skill_context_search_returns_chunks() -> None:
    client = TestClient(main_module.app)
    response = client.get(
        "/api/skills/document-assistant/context/search",
        params={"query": "文档 摘要"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["skill_id"] == "document-assistant"
    assert payload["chunks"]


def test_api_skill_cache_status_reports_redis_ping(monkeypatch) -> None:
    async def fake_ping_redis() -> bool:
        return True

    monkeypatch.setattr(skills_router_module, "ping_redis", fake_ping_redis)

    client = TestClient(main_module.app)
    response = client.get("/api/skills/cache/status")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "message": "Redis 已连接，可用于 skill 会话缓存。",
    }


def test_api_skill_cache_refresh_reports_ttl(monkeypatch) -> None:
    async def fake_refresh_conversation_state_ttl(
        conversation_id: str,
    ) -> tuple[bool, int]:
        assert conversation_id == "conversation-1"
        return True, 3600

    monkeypatch.setattr(
        skills_router_module,
        "refresh_conversation_state_ttl",
        fake_refresh_conversation_state_ttl,
    )

    client = TestClient(main_module.app)
    response = client.post("/api/skills/cache/conversations/conversation-1/refresh")

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "conversation-1",
        "exists": True,
        "ttl_seconds": 3600,
        "message": "会话缓存 TTL 已刷新。",
    }


def test_api_skill_cache_delete_clears_state(monkeypatch) -> None:
    async def fake_clear_conversation_state(conversation_id: str) -> bool:
        assert conversation_id == "conversation-1"
        return True

    async def fake_get_conversation_state_ttl_seconds(
        conversation_id: str,
    ) -> int:
        assert conversation_id == "conversation-1"
        return -2

    monkeypatch.setattr(
        skills_router_module,
        "clear_conversation_state",
        fake_clear_conversation_state,
    )
    monkeypatch.setattr(
        skills_router_module,
        "get_conversation_state_ttl_seconds",
        fake_get_conversation_state_ttl_seconds,
    )

    client = TestClient(main_module.app)
    response = client.delete("/api/skills/cache/conversations/conversation-1")

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "conversation-1",
        "exists": False,
        "ttl_seconds": -2,
        "message": "会话缓存已清理。",
    }


def test_compact_summary_excludes_compacted_chunks_from_full_injection() -> None:
    state = SkillConversationState(
        conversation_id="conversation-1",
        skill_id="document-assistant",
        system_prompt="test",
        compact_summary="保留摘要",
        compacted_chunk_ids=["chunk-1"],
    )
    loaded_chunks = [
        SkillContextChunk(
            id="chunk-1",
            skill_id="document-assistant",
            source_path="SKILL.md",
            title="旧规则",
            preview="旧规则预览",
            content="这一段应该只存在于摘要里",
        ),
        SkillContextChunk(
            id="chunk-2",
            skill_id="document-assistant",
            source_path="references/rule.md",
            title="新规则",
            preview="新规则预览",
            content="这一段应该完整注入",
        ),
    ]

    budget_text = _build_skill_context_budget_text(state, loaded_chunks)

    assert budget_text is not None
    assert "保留摘要" in budget_text
    assert "这一段应该完整注入" in budget_text
    assert "这一段应该只存在于摘要里" not in budget_text


def test_local_compact_summary_contains_chunk_titles() -> None:
    summary = _build_local_compact_summary(
        [
            SkillContextChunk(
                id="chunk-1",
                skill_id="document-assistant",
                source_path="SKILL.md",
                title="工作方式",
                preview="工作方式预览",
                content="先识别用户目标，再结合文档内容进行整理和回答。",
            )
        ]
    )

    assert "工作方式" in summary
    assert "先识别用户目标" in summary
