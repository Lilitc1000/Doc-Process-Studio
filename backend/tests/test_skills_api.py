from fastapi.testclient import TestClient

import doc_process_studio.main as main_module


def test_api_skills_returns_available_skill_interfaces() -> None:
    client = TestClient(main_module.app)
    response = client.get("/api/skills")

    assert response.status_code == 200

    payload = response.json()
    assert payload["default_skill_id"] == "document-assistant"
    assert any(
        skill["id"] == "document-assistant"
        and skill["display_name"] == "文档助手"
        for skill in payload["skills"]
    )
