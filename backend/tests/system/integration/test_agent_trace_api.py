from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.system.router.agent_traces as trace_router_module


def test_agent_trace_api_returns_trace_payload(monkeypatch, auth_headers) -> None:
    async def fake_load_agent_trace(*, tenant_id: str, trace_id: str):
        assert tenant_id == "tenant-a"
        assert trace_id == "trace-1"
        return {
            "trace_id": "trace-1",
            "events": [{"type": "planner"}],
        }

    monkeypatch.setattr(trace_router_module, "load_agent_trace", fake_load_agent_trace)
    client = TestClient(main_module.app)
    response = client.get("/api/system/agent-traces/trace-1?tenant_id=tenant-a", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["trace_id"] == "trace-1"
    assert response.json()["payload"]["events"][0]["type"] == "planner"


def test_agent_trace_api_returns_404_when_missing(monkeypatch, auth_headers) -> None:
    async def fake_load_agent_trace(*, tenant_id: str, trace_id: str):
        assert tenant_id == "default"
        assert trace_id == "trace-404"
        return None

    monkeypatch.setattr(trace_router_module, "load_agent_trace", fake_load_agent_trace)
    client = TestClient(main_module.app)
    response = client.get("/api/system/agent-traces/trace-404", headers=auth_headers)
    assert response.status_code == 404

