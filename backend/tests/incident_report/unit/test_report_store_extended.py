from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doc_process_studio.incident_report.service.report_store import (
    _CLEAR_SENTINEL,
    create_comment_record,
    create_report_record,
    delete_report_record,
    generate_ref_no,
    list_comment_records,
    list_reports,
    load_report_orm,
    update_report_record,
)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


async def test_generate_ref_no(mock_session):
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = "DAS-0042"
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await generate_ref_no()
    assert result == "DAS-0043"


async def test_generate_ref_no_empty(mock_session):
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await generate_ref_no()
    assert result == "DAS-0001"


async def test_create_report_record(mock_session):
    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await create_report_record(
            report_id="rep-1",
            ref_no="DAS-0001",
            title="测试报告",
            reporter_id="usr_test",
        )
    assert result is not None
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


async def test_create_report_record_with_all_fields(mock_session):
    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await create_report_record(
            report_id="rep-2",
            ref_no="DAS-0002",
            title="完整报告",
            reporter_id="usr_test",
            severity="P1",
            system="网络",
            site_id="SITE-02",
            form_data={"key": "val"},
        )
    assert result is not None


async def test_load_report_orm_found(mock_session):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
    from datetime import UTC, datetime

    report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试",
        status="draft",
        reporter_id="usr_test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = report
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await load_report_orm("rep-1")
    assert result is not None
    assert result.id == "rep-1"


async def test_load_report_orm_not_found(mock_session):
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await load_report_orm("nonexistent")
    assert result is None


async def test_update_report_record_found(mock_session):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
    from datetime import UTC, datetime

    report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="旧标题",
        status="draft",
        reporter_id="usr_test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = report
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await update_report_record("rep-1", title="新标题")
    assert result is not None
    mock_session.commit.assert_called_once()


async def test_update_report_record_not_found(mock_session):
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await update_report_record("nonexistent", title="新标题")
    assert result is None


async def test_update_report_record_clear_sentinel(mock_session):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
    from datetime import UTC, datetime

    report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="标题",
        status="draft",
        severity="P2",
        reporter_id="usr_test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = report
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await update_report_record("rep-1", severity=_CLEAR_SENTINEL)
    assert result is not None


async def test_update_report_record_ignores_invalid_field(mock_session):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
    from datetime import UTC, datetime

    report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="标题",
        status="draft",
        reporter_id="usr_test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = report
    mock_session.execute.return_value = mock_scalar

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await update_report_record("rep-1", nonexistent_field="value")
    assert result is not None


async def test_delete_report_record_deleted(mock_session):
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await delete_report_record("rep-1")
    assert result is True


async def test_delete_report_record_not_found(mock_session):
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await delete_report_record("nonexistent")
    assert result is False


async def test_list_reports_no_filters(mock_session):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentReport
    from datetime import UTC, datetime

    report = IncidentReport(
        id="rep-1",
        ref_no="DAS-0001",
        title="测试",
        status="draft",
        reporter_id="usr_test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_count_scalar = MagicMock()
    mock_count_scalar.scalar_one.return_value = 1

    mock_list_result = MagicMock()
    mock_list_result.scalars.return_value.all.return_value = [report]

    mock_session.execute.side_effect = [mock_count_scalar, mock_list_result]

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        records, total = await list_reports()
    assert total == 1
    assert len(records) == 1


async def test_list_reports_with_status_filter(mock_session):
    mock_count_scalar = MagicMock()
    mock_count_scalar.scalar_one.return_value = 0
    mock_list_result = MagicMock()
    mock_list_result.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [mock_count_scalar, mock_list_result]

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        records, total = await list_reports(status="draft")
    assert total == 0


async def test_list_reports_with_search(mock_session):
    mock_count_scalar = MagicMock()
    mock_count_scalar.scalar_one.return_value = 0
    mock_list_result = MagicMock()
    mock_list_result.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [mock_count_scalar, mock_list_result]

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        records, total = await list_reports(search="关键词")
    assert total == 0


async def test_list_reports_with_date_range(mock_session):
    from datetime import UTC, datetime

    mock_count_scalar = MagicMock()
    mock_count_scalar.scalar_one.return_value = 0
    mock_list_result = MagicMock()
    mock_list_result.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [mock_count_scalar, mock_list_result]

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        records, total = await list_reports(
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 12, 31, tzinfo=UTC),
        )
    assert total == 0


async def test_create_comment_record(mock_session):
    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await create_comment_record(
            comment_id="cmt-1",
            report_id="rep-1",
            author_id="usr_test",
            content="这是一条评论",
        )
    assert result is not None
    mock_session.add.assert_called_once()


async def test_create_comment_record_with_parent(mock_session):
    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await create_comment_record(
            comment_id="cmt-2",
            report_id="rep-1",
            author_id="usr_test",
            content="回复评论",
            parent_id="cmt-1",
        )
    assert result is not None


async def test_list_comment_records(mock_session):
    from doc_process_studio.incident_report.models.incident_report_orm import IncidentComment
    from datetime import UTC, datetime

    comment = IncidentComment(
        id="cmt-1",
        report_id="rep-1",
        author_id="usr_test",
        content="评论内容",
        created_at=datetime.now(UTC),
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [comment]
    mock_session.execute.return_value = mock_result

    with patch(
        "doc_process_studio.incident_report.service.report_store.async_session_factory"
    ) as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await list_comment_records("rep-1")
    assert len(result) == 1
