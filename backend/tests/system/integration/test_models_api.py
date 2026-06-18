from typing import Any

import pytest
from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
from doc_process_studio.core.ollama import extract_model_names
from doc_process_studio.system.infrastructure.dependencies import get_model_query_service


def test_extract_model_names_supports_multiple_payload_shapes() -> None:
    payload = {
        "models": [
            {"name": "qwen2.5:7b"},
            {"model": "llama3.1:8b"},
            {"id": "mistral:latest"},
            {"name": "qwen2.5:7b"},
        ]
    }

    assert extract_model_names(payload) == [
        "qwen2.5:7b",
        "llama3.1:8b",
        "mistral:latest",
    ]


class FakeModelQueryService:
    """测试用 ModelQueryService 替身。"""

    def __init__(self) -> None:
        self.models: list[str] = []
        self.calls: dict[str, list[Any]] = {}

    async def list_remote_models(self) -> list[str]:
        self.calls.setdefault("list_remote_models", []).append(())
        return self.models


@pytest.fixture()
def fake_model_service():
    service = FakeModelQueryService()
    main_module.app.dependency_overrides[get_model_query_service] = lambda: service
    yield service
    main_module.app.dependency_overrides.pop(get_model_query_service, None)


def test_api_models_returns_remote_model_names(fake_model_service: FakeModelQueryService, auth_headers) -> None:
    fake_model_service.models = ["qwen2.5:7b", "deepseek-r1:14b"]

    client = TestClient(main_module.app)
    response = client.get("/api/models", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "models": [
            {"name": "qwen2.5:7b"},
            {"name": "deepseek-r1:14b"},
        ]
    }
    assert fake_model_service.calls.get("list_remote_models") == [()]
