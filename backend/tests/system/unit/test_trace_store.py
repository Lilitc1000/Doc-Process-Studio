import asyncio

import doc_process_studio.system.service.trace_store as trace_store_module
from doc_process_studio.system.service.trace_store import (
    build_agent_trace_key,
    build_agent_trace_conversation_index_key,
    _encode_trace_index_member,
    _decode_trace_index_member,
    save_agent_trace,
    load_agent_trace,
    delete_agent_traces_for_conversation,
    AgentTraceRecorder,
)


class _FakeRedis:
    def __init__(self):
        self._store = {}
        self._sets = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, **kwargs):
        self._store[key] = value

    async def sadd(self, key, *members):
        if key not in self._sets:
            self._sets[key] = set()
        self._sets[key].update(members)
        return len(members)

    async def smembers(self, key):
        return self._sets.get(key, set())

    async def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
            if k in self._sets:
                del self._sets[k]
                count += 1
        return count

    async def expire(self, key, seconds):
        return True


def test_build_agent_trace_key():
    key = build_agent_trace_key(tenant_id="tenant-1", trace_id="trace-abc")
    assert "tenant-1" in key
    assert "trace-abc" in key


def test_build_agent_trace_conversation_index_key():
    key = build_agent_trace_conversation_index_key(conversation_id="conv-1")
    assert "conv-1" in key


def test_encode_decode_trace_index_member():
    encoded = _encode_trace_index_member(tenant_id="t1", trace_id="tr1")
    decoded = _decode_trace_index_member(encoded)
    assert decoded == ("t1", "tr1")


def test_decode_trace_index_member_invalid():
    assert _decode_trace_index_member("not json") is None
    assert _decode_trace_index_member('["only_one"]') is None
    assert _decode_trace_index_member('["", ""]') is None


def test_save_and_load_agent_trace(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(trace_store_module, "get_redis_client", lambda: fake)
    monkeypatch.setattr(trace_store_module, "set_json", fake.set)
    monkeypatch.setattr(trace_store_module, "get_json", fake.get)

    payload = {"trace_id": "tr1", "events": []}
    asyncio.run(
        save_agent_trace(
            tenant_id="t1",
            trace_id="tr1",
            conversation_id="conv-1",
            payload=payload,
        )
    )

    result = asyncio.run(load_agent_trace(tenant_id="t1", trace_id="tr1"))
    assert result is not None
    assert result["trace_id"] == "tr1"


def test_load_agent_trace_missing(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(trace_store_module, "get_json", fake.get)

    result = asyncio.run(load_agent_trace(tenant_id="t1", trace_id="missing"))
    assert result is None


def test_save_agent_trace_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(trace_store_module.settings, "agent_trace_store_enabled", False)
    fake = _FakeRedis()
    monkeypatch.setattr(trace_store_module, "get_redis_client", lambda: fake)

    asyncio.run(
        save_agent_trace(
            tenant_id="t1",
            trace_id="tr1",
            conversation_id="conv-1",
            payload={},
        )
    )
    assert len(fake._store) == 0


def test_save_agent_trace_skips_empty_ids(monkeypatch):
    monkeypatch.setattr(trace_store_module.settings, "agent_trace_store_enabled", True)
    fake = _FakeRedis()
    monkeypatch.setattr(trace_store_module, "get_redis_client", lambda: fake)

    asyncio.run(
        save_agent_trace(
            tenant_id="t1",
            trace_id="",
            conversation_id="conv-1",
            payload={},
        )
    )
    assert len(fake._store) == 0


def test_delete_agent_traces_for_conversation(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(trace_store_module, "get_redis_client", lambda: fake)
    monkeypatch.setattr(trace_store_module, "set_json", fake.set)
    monkeypatch.setattr(trace_store_module, "get_json", fake.get)

    asyncio.run(
        save_agent_trace(
            tenant_id="t1",
            trace_id="tr1",
            conversation_id="conv-1",
            payload={"trace_id": "tr1"},
        )
    )

    count = asyncio.run(
        delete_agent_traces_for_conversation(conversation_id="conv-1")
    )
    assert count >= 1


def test_delete_agent_traces_for_empty_conversation(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(trace_store_module, "get_redis_client", lambda: fake)

    count = asyncio.run(
        delete_agent_traces_for_conversation(conversation_id="")
    )
    assert count == 0


def test_agent_trace_recorder():
    recorder = AgentTraceRecorder(
        trace_id="tr1",
        tenant_id="t1",
        conversation_id="conv-1",
        user_message_id="msg-1",
        model="test-model",
        reranker_model="reranker",
    )
    recorder.add_event(event_type="test", detail={"key": "value"})
    recorder.set_planner({"skill": "incident-report"})
    recorder.add_round(round_index=0, detail={"tool": "search"})
    recorder.set_final(done_reason="stop", error=None)

    assert recorder.payload["trace_id"] == "tr1"
    assert len(recorder.payload["events"]) == 1
    assert recorder.payload["planner"]["skill"] == "incident-report"
    assert len(recorder.payload["rounds"]) == 1
    assert recorder.payload["final"]["done_reason"] == "stop"


def test_agent_trace_recorder_flush(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(trace_store_module, "get_redis_client", lambda: fake)
    monkeypatch.setattr(trace_store_module, "set_json", fake.set)
    monkeypatch.setattr(trace_store_module, "get_json", fake.get)

    recorder = AgentTraceRecorder(
        trace_id="tr1",
        tenant_id="t1",
        conversation_id="conv-1",
        user_message_id="msg-1",
        model="test-model",
        reranker_model="reranker",
    )
    asyncio.run(recorder.flush())
