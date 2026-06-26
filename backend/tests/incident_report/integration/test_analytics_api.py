from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.common.security.security import create_access_token
from doc_process_studio.incident_report.application.dtos import (
    IncidentAnalyticsOverview,
    IncidentAnalyticsTrend,
)
from doc_process_studio.incident_report.infrastructure.dependencies import (
    get_analytics_service,
)
from doc_process_studio.incident_report.router.analytics import router as analytics_router


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(analytics_router)
    return app


def _auth_headers(user_id: str = "usr_test", username: str = "testuser") -> dict:
    token = create_access_token(user_id, username)
    return {"Authorization": f"Bearer {token}"}


def test_analytics_overview_requires_auth():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/api/incident-report/analytics/overview")
    assert resp.status_code in (401, 403)


def test_analytics_trend_requires_auth():
    app = _create_test_app()
    client = TestClient(app)
    resp = client.get("/api/incident-report/analytics/trend")
    assert resp.status_code in (401, 403)


def test_analytics_overview_returns_structure():
    app = _create_test_app()

    fake_service = AsyncMock()
    fake_service.get_overview.return_value = IncidentAnalyticsOverview(
        total_count=5,
        draft_count=1,
        pending_count=2,
        rejected_count=0,
        approved_count=0,
        in_progress_count=1,
        closed_count=3,
        avg_resolution_hours=12.5,
    )
    app.dependency_overrides[get_analytics_service] = lambda: fake_service

    client = TestClient(app)
    resp = client.get(
        "/api/incident-report/analytics/overview",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_count" in data
    assert "draft_count" in data
    assert "pending_count" in data
    assert "rejected_count" in data
    assert "approved_count" in data
    assert "in_progress_count" in data
    assert "closed_count" in data


def test_analytics_trend_returns_list():
    app = _create_test_app()

    fake_service = AsyncMock()
    fake_service.get_trend.return_value = [IncidentAnalyticsTrend(date="2026-04-25", count=3)]
    app.dependency_overrides[get_analytics_service] = lambda: fake_service

    client = TestClient(app)
    resp = client.get(
        "/api/incident-report/analytics/trend",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
