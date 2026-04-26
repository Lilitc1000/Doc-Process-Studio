import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_process_studio.incident_report.router.reports import router as reports_router
from doc_process_studio.incident_report.router.roles import router as roles_router
from doc_process_studio.incident_report.router.analytics import router as analytics_router


@pytest.fixture()
def app():
    _app = FastAPI()
    _app.include_router(reports_router)
    _app.include_router(roles_router)
    _app.include_router(analytics_router)
    return _app


@pytest.fixture()
def client(app):
    return TestClient(app)
