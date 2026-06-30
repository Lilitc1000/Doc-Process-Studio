"""仓储实现扩展测试。

测试 SqlAlchemyReportRepository、SequentialRefNoGenerator、SqlCommentRepository
的核心方法在 mock session 下的行为。
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doc_process_studio.incident_report.domain.entities.report import Report
from doc_process_studio.incident_report.domain.entities.status import ReportStatus
from doc_process_studio.incident_report.infrastructure.persistence.incident_report_orm import (
    IncidentComment,
    IncidentReport,
)
from doc_process_studio.incident_report.infrastructure.repositories.comment_repository import (
    SqlCommentRepository,
)
from doc_process_studio.incident_report.infrastructure.repositories.report_repository import (
    SequentialRefNoGenerator,
    SqlAlchemyReportRepository,
)


def _make_report_orm(**overrides: Any) -> IncidentReport:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = dict(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status="draft",
        reporter_id="usr_test",
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return IncidentReport(**defaults)


def _make_report_aggregate(**overrides: Any) -> Report:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = dict(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试报告",
        status=ReportStatus.DRAFT,
        reporter_id="usr_test",
        severity="P2",
        system="数据库",
        site_id="SITE-01",
        fault_date=now,
        form_data={},
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Report(**defaults)


@pytest.fixture
def mock_session() -> Any:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


# --- SequentialRefNoGenerator ---


async def test_ref_no_generator_increments(mock_session: Any) -> None:
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = "DAS-0042"
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        gen = SequentialRefNoGenerator()
        result = await gen.next()
    assert result == "DAS-0043"


async def test_ref_no_generator_starts_at_1(mock_session: Any) -> None:
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        gen = SequentialRefNoGenerator()
        result = await gen.next()
    assert result == "DAS-0001"


# --- SqlAlchemyReportRepository.add ---


async def test_repo_add_creates_report(mock_session: Any) -> None:
    mock_session.refresh = AsyncMock()

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_user_dir = AsyncMock()
        mock_user_dir.resolve_usernames = AsyncMock(return_value={})
        mock_ref_no_gen = AsyncMock()
        mock_ref_no_gen.next = AsyncMock(return_value="DAS-0001")

        repo = SqlAlchemyReportRepository(user_dir=mock_user_dir, ref_no_gen=mock_ref_no_gen)
        report = _make_report_aggregate()
        result = await repo.add(report)
    assert result is not None
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


# --- SqlAlchemyReportRepository.get ---


async def test_repo_get_found(mock_session: Any) -> None:
    orm = _make_report_orm()
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = orm
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_user_dir = AsyncMock()
        mock_ref_no_gen = AsyncMock()
        repo = SqlAlchemyReportRepository(user_dir=mock_user_dir, ref_no_gen=mock_ref_no_gen)
        result = await repo.get("rep-1")
    assert result is not None
    assert result.id == "rep-1"


async def test_repo_get_not_found(mock_session: Any) -> None:
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_user_dir = AsyncMock()
        mock_ref_no_gen = AsyncMock()
        repo = SqlAlchemyReportRepository(user_dir=mock_user_dir, ref_no_gen=mock_ref_no_gen)
        result = await repo.get("nonexistent")
    assert result is None


# --- SqlAlchemyReportRepository.update ---


async def test_repo_update_found(mock_session: Any) -> None:
    orm = _make_report_orm()
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = orm
    mock_session.execute.return_value = mock_scalar
    mock_session.refresh = AsyncMock()

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_user_dir = AsyncMock()
        mock_ref_no_gen = AsyncMock()
        repo = SqlAlchemyReportRepository(user_dir=mock_user_dir, ref_no_gen=mock_ref_no_gen)
        report = _make_report_aggregate(title="新标题")
        result = await repo.update(report)
    assert result is not None
    mock_session.commit.assert_called_once()


async def test_repo_update_not_found(mock_session: Any) -> None:
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_user_dir = AsyncMock()
        mock_ref_no_gen = AsyncMock()
        repo = SqlAlchemyReportRepository(user_dir=mock_user_dir, ref_no_gen=mock_ref_no_gen)
        report = _make_report_aggregate()
        result = await repo.update(report)
    assert result is None


# --- SqlAlchemyReportRepository.delete ---


async def test_repo_delete_found(mock_session: Any) -> None:
    orm = _make_report_orm()
    mock_session.get = AsyncMock(return_value=orm)
    mock_session.execute = AsyncMock()

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_user_dir = AsyncMock()
        mock_ref_no_gen = AsyncMock()
        repo = SqlAlchemyReportRepository(user_dir=mock_user_dir, ref_no_gen=mock_ref_no_gen)
        result = await repo.delete("rep-1")
    assert result is True


async def test_repo_delete_not_found(mock_session: Any) -> None:
    mock_session.get = AsyncMock(return_value=None)

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.report_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_user_dir = AsyncMock()
        mock_ref_no_gen = AsyncMock()
        repo = SqlAlchemyReportRepository(user_dir=mock_user_dir, ref_no_gen=mock_ref_no_gen)
        result = await repo.delete("nonexistent")
    assert result is False


# --- SqlCommentRepository ---


async def test_comment_repo_add(mock_session: Any) -> None:
    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.comment_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = SqlCommentRepository()
        result = await repo.add(
            comment_id="cmt-1",
            report_id="rep-1",
            author_id="usr_test",
            content="这是一条评论",
        )
    assert result is not None
    mock_session.add.assert_called_once()


async def test_comment_repo_add_with_parent(mock_session: Any) -> None:
    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.comment_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = SqlCommentRepository()
        result = await repo.add(
            comment_id="cmt-2",
            report_id="rep-1",
            author_id="usr_test",
            content="回复评论",
            parent_id="cmt-1",
        )
    assert result is not None


async def test_comment_repo_list_by_report(mock_session: Any) -> None:
    now = datetime.now(UTC)
    comment = IncidentComment(
        id="cmt-1",
        report_id="rep-1",
        author_id="usr_test",
        content="评论内容",
        created_at=now,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [comment]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.infrastructure.repositories.comment_repository.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = SqlCommentRepository()
        result = await repo.list_by_report("rep-1")
    assert len(result) == 1
