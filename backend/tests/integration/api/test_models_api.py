from fastapi.testclient import TestClient

import doc_process_studio.main as main_module
import doc_process_studio.system.router.models as models_router_module
from doc_process_studio.core.ollama import extract_model_names


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


def test_api_models_returns_remote_model_names(monkeypatch) -> None:
    async def fake_fetch_remote_model_names() -> list[str]:
        return ["qwen2.5:7b", "deepseek-r1:14b"]

    monkeypatch.setattr(
        models_router_module,
        "fetch_remote_model_names",
        fake_fetch_remote_model_names,
    )

    client = TestClient(main_module.app)
    response = client.get("/api/models")

    assert response.status_code == 200
    assert response.json() == {
        "models": [
            {"name": "qwen2.5:7b"},
            {"name": "deepseek-r1:14b"},
        ]
    }
