from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.core.security import create_access_token
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

    mock_result = MagicMock()
    mock_result.scalar_one.side_effect = [5, 2, 1, 3]
    mock_result.scalar_one_or_none.return_value = 12.5

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session)

    async def _fake_has_permission(user_id, permission):
        return True

    with patch(
        "doc_process_studio.incident_report.router.analytics.async_session_factory",
        mock_factory,
    ), patch(
        "doc_process_studio.incident_report.router.analytics.has_permission",
        _fake_has_permission,
    ), patch(
        "doc_process_studio.shared.dtutils.utcnow",
        return_value=__import__("datetime").datetime(2026, 4, 25, 12, 0, 0),
    ):
        client = TestClient(app)
        resp = client.get(
            "/api/incident-report/analytics/overview",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_this_month" in data
        assert "pending_count" in data
        assert "in_progress_count" in data
        assert "closed_this_month" in data


def test_analytics_trend_returns_list():
    app = _create_test_app()

    mock_row = MagicMock()
    mock_row.day = __import__("datetime").date(2026, 4, 25)
    mock_row.count = 3

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session)

    async def _fake_has_permission(user_id, permission):
        return True

    with patch(
        "doc_process_studio.incident_report.router.analytics.async_session_factory",
        mock_factory,
    ), patch(
        "doc_process_studio.incident_report.router.analytics.has_permission",
        _fake_has_permission,
    ), patch(
        "doc_process_studio.shared.dtutils.utcnow",
        return_value=__import__("datetime").datetime(2026, 4, 25, 12, 0, 0),
    ):
        client = TestClient(app)
        resp = client.get(
            "/api/incident-report/analytics/trend",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
