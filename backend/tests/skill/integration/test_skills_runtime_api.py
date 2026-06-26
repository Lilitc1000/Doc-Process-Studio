from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
from doc_process_studio.skill.application.contracts import SkillServiceContract
from doc_process_studio.skill.application.dtos.catalog import SkillInterfaceConfig
from doc_process_studio.skill.application.dtos.runtime import (
    SkillContextChunk,
    SkillConversationState,
)
from doc_process_studio.skill.infrastructure.context_packer import (
    _build_local_summary_from_chunks,
    build_skill_context_budget_text,
)
from doc_process_studio.skill.infrastructure.dependencies import get_skill_service


class _FakeSkillService(SkillServiceContract):
    """测试用 SkillService 桩，绕过真实端口依赖。"""

    def __init__(
        self,
        *,
        chunks: list[SkillContextChunk] | None = None,
        refresh_result: tuple[bool, int] | None = None,
        delete_result: tuple[bool, int] | None = None,
    ) -> None:
        self._chunks = chunks
        self._refresh_result = refresh_result
        self._delete_result = delete_result

    def list_skills(self) -> list[SkillInterfaceConfig]:
        return []

    async def search_context(self, skill_id: str, query: str) -> list[SkillContextChunk]:
        _ = (skill_id, query)
        return self._chunks or []

    async def refresh_conversation_cache(self, conversation_id: str, tenant_id: str = "default") -> tuple[bool, int]:
        assert conversation_id == "conversation-1"
        assert tenant_id == "default"
        return self._refresh_result or (True, 3600)

    async def delete_conversation_cache(self, conversation_id: str, tenant_id: str = "default") -> tuple[bool, int]:
        assert conversation_id == "conversation-1"
        assert tenant_id == "default"
        return self._delete_result or (True, -2)


def _install_fake_service(monkeypatch, fake: _FakeSkillService) -> None:
    monkeypatch.setitem(
        main_module.app.dependency_overrides,
        get_skill_service,
        lambda: fake,
    )


def test_api_skill_context_search_returns_chunks(monkeypatch, auth_headers) -> None:
    fake = _FakeSkillService(
        chunks=[
            SkillContextChunk(
                id="chunk-1",
                skill_id="document-assistant",
                source_path="SKILL.md",
                title="文档摘要",
                preview="文档摘要预览",
                content="文档摘要内容",
            )
        ]
    )
    _install_fake_service(monkeypatch, fake)

    client = TestClient(main_module.app)
    response = client.get(
        "/api/skills/document-assistant/context/search",
        params={"query": "文档 摘要"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["skill_id"] == "document-assistant"
    assert payload["chunks"]


def test_api_skill_cache_status_reports_redis_ping(monkeypatch, auth_headers) -> None:
    import doc_process_studio.skill.router.routes as routes_module

    async def fake_ping_redis() -> bool:
        return True

    monkeypatch.setattr(routes_module, "ping_redis", fake_ping_redis)

    client = TestClient(main_module.app)
    response = client.get("/api/skills/cache/status", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "message": "Redis 已连接，可用于 skill 会话缓存。",
    }


def test_api_skill_cache_refresh_reports_ttl(monkeypatch, auth_headers) -> None:
    fake = _FakeSkillService(refresh_result=(True, 3600))
    _install_fake_service(monkeypatch, fake)

    client = TestClient(main_module.app)
    response = client.post(
        "/api/skills/cache/conversations/conversation-1/refresh",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "conversation-1",
        "exists": True,
        "ttl_seconds": 3600,
        "message": "会话缓存 TTL 已刷新。",
    }


def test_api_skill_cache_delete_clears_state(monkeypatch, auth_headers) -> None:
    fake = _FakeSkillService(delete_result=(True, -2))
    _install_fake_service(monkeypatch, fake)

    client = TestClient(main_module.app)
    response = client.delete(
        "/api/skills/cache/conversations/conversation-1",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "conversation-1",
        "exists": False,
        "ttl_seconds": -2,
        "message": "会话缓存已清理。",
    }


def test_hierarchical_memory_excludes_compacted_chunks_from_full_injection() -> None:
    state = SkillConversationState(
        conversation_id="conversation-1",
        skill_id="document-assistant",
        system_prompt="test",
        short_term_memory="保留短期记忆",
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

    budget_text = build_skill_context_budget_text(state, loaded_chunks)

    assert budget_text is not None
    assert "保留短期记忆" in budget_text
    assert "这一段应该完整注入" in budget_text
    assert "这一段应该只存在于摘要里" not in budget_text


def test_local_short_term_summary_contains_chunk_titles() -> None:
    summary = _build_local_summary_from_chunks(
        chunks=[
            SkillContextChunk(
                id="chunk-1",
                skill_id="document-assistant",
                source_path="SKILL.md",
                title="工作方式",
                preview="工作方式预览",
                content="先识别用户目标，再结合文档内容进行整理和回答。",
            )
        ],
        title="短期记忆要点：",
        max_characters=500,
    )

    assert "工作方式" in summary
    assert "先识别用户目标" in summary
