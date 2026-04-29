import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doc_process_studio.incident_report.service.role import (
    assign_incident_role,
    get_user_incident_roles,
    get_user_permissions,
    has_any_permission,
    has_incident_role,
    has_permission,
    list_all_role_assignments,
    require_incident_role,
    revoke_incident_role,
)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


def test_get_user_incident_roles(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = [("reporter",), ("admin",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(get_user_incident_roles("usr_test"))
    assert result == {"reporter", "admin"}


def test_get_user_incident_roles_empty(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(get_user_incident_roles("usr_test"))
    assert result == set()


def test_has_incident_role_true(mock_session):
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = "reporter"
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(has_incident_role("usr_test", "reporter"))
    assert result is True


def test_has_incident_role_false(mock_session):
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(has_incident_role("usr_test", "admin"))
    assert result is False


def test_require_incident_role_true(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = [("reporter",), ("admin",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(require_incident_role("usr_test", ["admin", "verifier"]))
    assert result is True


def test_require_incident_role_false(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = [("reporter",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(require_incident_role("usr_test", ["admin", "verifier"]))
    assert result is False


def test_get_user_permissions(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = [("reporter",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(get_user_permissions("usr_test"))
    assert "report:create" in result
    assert "report:edit_own" in result
    assert "report:submit" in result
    assert "role:manage" not in result


def test_get_user_permissions_no_roles(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(get_user_permissions("usr_test"))
    assert result == set()


def test_has_permission_true(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = [("admin",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(has_permission("usr_test", "role:manage"))
    assert result is True


def test_has_permission_false(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = [("viewer",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(has_permission("usr_test", "role:manage"))
    assert result is False


def test_has_any_permission_true(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = [("verifier",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(has_any_permission("usr_test", {"report:audit", "role:manage"}))
    assert result is True


def test_has_any_permission_false(mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = [("viewer",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(has_any_permission("usr_test", {"report:audit", "role:manage"}))
    assert result is False


def test_assign_incident_role_new(mock_session):
    user_exists_result = MagicMock()
    user_exists_result.scalar_one_or_none.return_value = "usr_test"

    existing_role_result = MagicMock()
    existing_role_result.scalar_one_or_none.return_value = None

    mock_session.execute = AsyncMock(side_effect=[user_exists_result, existing_role_result])

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory, patch(
        "doc_process_studio.incident_report.service.role.generate_user_id",
        return_value="usr_generated",
    ):
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        asyncio.run(assign_incident_role("usr_test", "reporter", "usr_admin"))
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


def test_assign_incident_role_existing(mock_session):
    from doc_process_studio.incident_report.models.incident_report_role import IncidentReportUserRole

    existing = IncidentReportUserRole(id="usr_exist", user_id="usr_test", role_key="reporter", assigned_by="usr_admin")

    user_exists_result = MagicMock()
    user_exists_result.scalar_one_or_none.return_value = "usr_test"

    existing_role_result = MagicMock()
    existing_role_result.scalar_one_or_none.return_value = existing

    mock_session.execute = AsyncMock(side_effect=[user_exists_result, existing_role_result])

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        asyncio.run(assign_incident_role("usr_test", "reporter", "usr_admin"))
    mock_session.add.assert_not_called()


def test_assign_incident_role_invalid():
    with pytest.raises(ValueError, match="无效的角色标识"):
        asyncio.run(assign_incident_role("usr_test", "invalid_role", "usr_admin"))


def test_revoke_incident_role(mock_session):
    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        asyncio.run(revoke_incident_role("usr_test", "reporter"))
    mock_session.commit.assert_called_once()


def test_revoke_incident_role_invalid():
    with pytest.raises(ValueError, match="无效的角色标识"):
        asyncio.run(revoke_incident_role("usr_test", "invalid_role"))


def test_list_all_role_assignments(mock_session):
    from doc_process_studio.incident_report.models.incident_report_role import IncidentReportUserRole

    role1 = IncidentReportUserRole(id="ur1", user_id="usr_1", role_key="reporter", assigned_by="usr_admin")
    role2 = IncidentReportUserRole(id="ur2", user_id="usr_2", role_key="admin", assigned_by="usr_admin")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [role1, role2]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(list_all_role_assignments())
    assert len(result) == 2
