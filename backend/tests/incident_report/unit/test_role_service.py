import asyncio

import pytest

from doc_process_studio.incident_report.service.role import (
    get_user_incident_roles,
    has_incident_role,
    require_incident_role,
    assign_incident_role,
    revoke_incident_role,
)


def test_get_user_incident_roles_returns_set(monkeypatch):
    async def _fake_select_roles(user_id):
        return {"reporter", "admin"}

    import doc_process_studio.incident_report.service.role as role_module
    monkeypatch.setattr(role_module, "get_user_incident_roles", _fake_select_roles)

    result = asyncio.run(_fake_select_roles("usr_test"))
    assert "reporter" in result
    assert "admin" in result


def test_assign_incident_role_validates_role(monkeypatch):
    with pytest.raises(ValueError, match="无效的角色标识"):
        asyncio.run(assign_incident_role(
            user_id="usr_test",
            role="invalid_role",
            assigned_by="usr_admin",
        ))


def test_revoke_incident_role_validates_role(monkeypatch):
    with pytest.raises(ValueError, match="无效的角色标识"):
        asyncio.run(revoke_incident_role(
            user_id="usr_test",
            role="invalid_role",
        ))
