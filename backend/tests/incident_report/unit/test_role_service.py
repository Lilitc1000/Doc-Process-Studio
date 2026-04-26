import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doc_process_studio.incident_report.service.role import get_user_incident_roles


def test_get_user_incident_roles_returns_set():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [("reporter",), ("admin",)]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.role.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = asyncio.run(get_user_incident_roles("usr_test"))
    assert isinstance(result, set)
    assert "reporter" in result
    assert "admin" in result
