from typing import Any

import pytest
from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
from doc_process_studio.system.application.contracts import TraceQueryServiceContract
from doc_process_studio.system.infrastructure.dependencies import get_trace_query_service


class FakeTraceQueryService(TraceQueryServiceContract):
    """测试用 TraceQueryService 替身。"""

    def __init__(self) -> None:
        self.responses: dict[str, dict[str, Any] | None] = {}
        self.calls: dict[str, list[Any]] = {}

    async def get_trace(self, *, tenant_id: str, trace_id: str) -> dict[str, Any]:
        self.calls.setdefault("get_trace", []).append((tenant_id, trace_id))
        payload = self.responses.get(f"{tenant_id}:{trace_id}")
        if payload is None:
            from doc_process_studio.system.domain.errors import TraceNotFoundError

            raise TraceNotFoundError("未找到对应 trace_id 的回放记录。")
        return payload


@pytest.fixture()
def fake_trace_service():
    service = FakeTraceQueryService()
    main_module.app.dependency_overrides[get_trace_query_service] = lambda: service
    yield service
    main_module.app.dependency_overrides.pop(get_trace_query_service, None)


def test_agent_trace_api_returns_trace_payload(fake_trace_service: FakeTraceQueryService, auth_headers) -> None:
    fake_trace_service.responses["tenant-a:trace-1"] = {
        "trace_id": "trace-1",
        "events": [{"type": "planner"}],
    }

    client = TestClient(main_module.app)
    response = client.get("/api/system/agent-traces/trace-1?tenant_id=tenant-a", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["trace_id"] == "trace-1"
    assert response.json()["payload"]["events"][0]["type"] == "planner"
    assert fake_trace_service.calls.get("get_trace") == [("tenant-a", "trace-1")]


def test_agent_trace_api_returns_404_when_missing(fake_trace_service: FakeTraceQueryService, auth_headers) -> None:
    client = TestClient(main_module.app)
    response = client.get("/api/system/agent-traces/trace-404", headers=auth_headers)
    assert response.status_code == 404
    assert fake_trace_service.calls.get("get_trace") == [("default", "trace-404")]
