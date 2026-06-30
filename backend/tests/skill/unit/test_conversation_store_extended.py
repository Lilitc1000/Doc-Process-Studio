from typing import Any

import pytest

import doc_process_studio.skill.infrastructure.conversation_store as cs_module
from doc_process_studio.skill.application.dtos.runtime import ConversationAgentState, SkillConversationState


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, **_kwargs: Any) -> None:
        self._store[key] = value

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def expire(self, _key: Any, _seconds: Any) -> bool:
        return True

    async def ttl(self, _key: Any) -> Any:
        return -1


def test_build_conversation_state_key() -> None:
    key = cs_module.build_conversation_state_key("conv-1")
    assert "conv-1" in key


async def test_load_conversation_state_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cs_module, "get_json", fake.get)
    result = await cs_module.load_conversation_state("missing")
    assert result is None


async def test_save_and_load_conversation_state(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cs_module, "set_json", fake.set)
    monkeypatch.setattr(cs_module, "get_json", fake.get)

    state = ConversationAgentState(
        conversation_id="conv-1",
        skills_state={
            "skill-1": SkillConversationState(
                conversation_id="conv-1",
                skill_id="skill-1",
                system_prompt="test prompt",
            )
        },
    )
    await cs_module.save_conversation_state(state)
    loaded = await cs_module.load_conversation_state("conv-1")
    assert loaded is not None
    assert loaded.conversation_id == "conv-1"


async def test_refresh_conversation_state_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_refresh_ttl(_key: Any, **_kwargs: Any) -> bool:
        return True

    async def _fake_get_ttl(_key: Any) -> int:
        return 3600

    monkeypatch.setattr(cs_module, "refresh_ttl", _fake_refresh_ttl)
    monkeypatch.setattr(cs_module, "get_ttl_seconds", _fake_get_ttl)
    refreshed, ttl = await cs_module.refresh_conversation_state_ttl("conv-1")
    assert refreshed is True
    assert ttl == 3600


async def test_clear_conversation_state(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_delete_key(_key: Any) -> int:
        return 1

    monkeypatch.setattr(cs_module, "delete_key", _fake_delete_key)
    result = await cs_module.clear_conversation_state("conv-1")
    assert result is True


async def test_get_conversation_state_ttl_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(cs_module, "get_ttl_seconds", fake.ttl)
    result = await cs_module.get_conversation_state_ttl_seconds("conv-1")
    assert isinstance(result, int)
