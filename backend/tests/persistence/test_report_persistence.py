"""事故报告持久化集成测试（真实 PostgreSQL）。

只覆盖 mock session 测不出来的部分：SQL 是否写对、schema 是否对、
约束是否真的生效、事务隔离是否真的回滚。业务编排逻辑仍由 mock 单测负责。

运行方式（未配置 DSN 时整组 skip，普通 `uv run pytest` 依旧全绿）：
    uv run python scripts/init_test_db.py          # 建 dps_test 库
    DPS_TEST_DATABASE_URL=postgresql+asyncpg://admin:postgres_password@db:5432/dps_test \
        uv run pytest tests/persistence -m db
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from doc_process_studio.auth.infrastructure.persistence import User
from doc_process_studio.incident_report.domain.entities.report import Report
from doc_process_studio.incident_report.domain.entities.status import ReportStatus
from doc_process_studio.incident_report.infrastructure.persistence import (
    IncidentComment,
    IncidentReport,
)
from doc_process_studio.incident_report.infrastructure.repositories import (
    SequentialRefNoGenerator,
    SqlAlchemyReportRepository,
)

pytestmark = [pytest.mark.db, pytest.mark.asyncio(loop_scope="session")]

UserFactory = Callable[..., Coroutine[Any, Any, User]]


def _id(prefix: str) -> str:
    """生成符合 String(32) 主键长度约束的 id。"""
    return f"{prefix}{uuid4().hex[:12]}"


async def _insert_report_orm(
    db_session: AsyncSession,
    *,
    reporter_id: str,
    ref_no: str,
    title: str = "持久化测试报告",
) -> IncidentReport:
    """绕过聚合根直接写 ORM，用于验证数据库层约束与默认值。"""
    orm = IncidentReport(
        id=_id("r"),
        ref_no=ref_no,
        title=title,
        status="draft",
        reporter_id=reporter_id,
    )
    db_session.add(orm)
    await db_session.commit()
    return orm


async def test_save_and_reload_keeps_all_fields(
    user_factory: UserFactory,
    report_repository: SqlAlchemyReportRepository,
) -> None:
    """保存后重新读回，所有字段应完全一致。"""
    user = await user_factory()
    fault_date = datetime(2026, 4, 27, 8, 30, tzinfo=UTC)

    saved = await report_repository.add(
        Report.create(
            report_id=_id("r"),
            ref_no=f"DAS-{uuid4().hex[:8]}",
            title="闸机无法识别通行卡",
            reporter_id=user.user_id,
            severity="P1",
            system="收费系统",
            site_id="SITE-01",
            fault_date=fault_date,
            form_data={"manual_fault_symptom": "读卡失败"},
        )
    )
    reloaded = await report_repository.get(saved.id)

    assert reloaded is not None
    assert reloaded.title == "闸机无法识别通行卡"
    assert reloaded.status is ReportStatus.DRAFT
    assert reloaded.severity == "P1"
    assert reloaded.system == "收费系统"
    assert reloaded.site_id == "SITE-01"
    assert reloaded.form_data == {"manual_fault_symptom": "读卡失败"}
    assert reloaded.reporter_id == user.user_id
    assert reloaded.fault_date is not None
    assert reloaded.fault_date.astimezone(UTC).date() == fault_date.date()


async def test_created_at_and_updated_at_default_to_database_time(
    db_session: AsyncSession,
    user_factory: UserFactory,
) -> None:
    """不传时间戳时，created_at / updated_at 应由数据库 server_default 生成。"""
    user = await user_factory()
    orm = await _insert_report_orm(db_session, reporter_id=user.user_id, ref_no=f"DAS-{uuid4().hex[:8]}")

    db_now = await db_session.scalar(select(func.now()))

    assert orm.created_at is not None
    assert orm.updated_at is not None
    assert orm.created_at.tzinfo is not None
    assert db_now is not None
    assert abs((db_now - orm.created_at.astimezone(UTC)).total_seconds()) < 60


async def test_updated_at_bumps_on_update(
    db_session: AsyncSession,
    user_factory: UserFactory,
) -> None:
    """只改业务字段（不手填 updated_at）时，onupdate=now() 应生效。"""
    user = await user_factory()
    orm = await _insert_report_orm(db_session, reporter_id=user.user_id, ref_no=f"DAS-{uuid4().hex[:8]}")

    stale = datetime(2020, 1, 1, tzinfo=UTC)
    orm.updated_at = stale
    await db_session.commit()

    orm.title = "改后的标题"
    await db_session.commit()
    await db_session.refresh(orm)

    assert orm.updated_at is not None
    assert orm.updated_at.astimezone(UTC) > stale


async def test_ref_no_unique_constraint_is_enforced(
    db_session: AsyncSession,
    user_factory: UserFactory,
) -> None:
    """ref_no 唯一约束必须真的生效（并发重号是线上真实风险）。"""
    user = await user_factory()
    ref_no = f"DAS-DUP-{uuid4().hex[:6]}"
    await _insert_report_orm(db_session, reporter_id=user.user_id, ref_no=ref_no)

    with pytest.raises(IntegrityError):
        await _insert_report_orm(db_session, reporter_id=user.user_id, ref_no=ref_no)

    await db_session.rollback()  # 让会话恢复到可用状态


async def test_reporter_id_foreign_key_is_enforced(
    db_session: AsyncSession,
    user_factory: UserFactory,
) -> None:
    """reporter_id 必须指向存在的用户，否则数据库应拒绝写入。"""
    await user_factory()

    with pytest.raises(IntegrityError):
        await _insert_report_orm(db_session, reporter_id="ghost-user-id", ref_no=f"DAS-{uuid4().hex[:8]}")

    await db_session.rollback()


async def test_comments_are_cascade_deleted_by_database(
    db_session: AsyncSession,
    user_factory: UserFactory,
) -> None:
    """删除报告时，数据库层的 ON DELETE CASCADE 应带走评论。"""
    user = await user_factory()
    report = await _insert_report_orm(db_session, reporter_id=user.user_id, ref_no=f"DAS-{uuid4().hex[:8]}")
    db_session.add(
        IncidentComment(
            id=_id("c"),
            report_id=report.id,
            author_id=user.user_id,
            content="这是一条测试评论",
        )
    )
    await db_session.commit()

    await db_session.execute(delete(IncidentReport).where(IncidentReport.id == report.id))
    await db_session.commit()

    remaining = await db_session.scalar(
        select(func.count()).select_from(IncidentComment).where(IncidentComment.report_id == report.id)
    )
    assert remaining == 0


async def test_repository_delete_removes_comments(
    db_session: AsyncSession,
    user_factory: UserFactory,
    report_repository: SqlAlchemyReportRepository,
) -> None:
    """仓储 delete 应删除报告及其评论，不存在的 id 返回 False。"""
    user = await user_factory()
    report = await _insert_report_orm(db_session, reporter_id=user.user_id, ref_no=f"DAS-{uuid4().hex[:8]}")
    db_session.add(
        IncidentComment(
            id=_id("c"),
            report_id=report.id,
            author_id=user.user_id,
            content="待级联删除",
        )
    )
    await db_session.commit()

    assert await report_repository.delete(report.id) is True
    assert await report_repository.get(report.id) is None
    assert await report_repository.delete("not-exist-id") is False


async def test_jsonb_roundtrip_preserves_nested_structures(
    user_factory: UserFactory,
    report_repository: SqlAlchemyReportRepository,
) -> None:
    """JSONB 字段往返：中文、None、嵌套结构、数字与布尔都应原样保留。"""
    user = await user_factory()
    payload: dict[str, Any] = {
        "manual_fault_symptom": "车道栏杆机不落杆，标点也要保真：，。！",
        "manual_materials_used": None,
        "nested": {"level1": {"level2": ["甲", "乙", 3]}},
        "count": 12,
        "confirmed": True,
        "empty_list": [],
    }

    saved = await report_repository.add(
        Report.create(
            report_id=_id("r"),
            ref_no=f"DAS-{uuid4().hex[:8]}",
            title="JSONB 往返测试",
            reporter_id=user.user_id,
            form_data=payload,
        )
    )
    reloaded = await report_repository.get(saved.id)

    assert reloaded is not None
    assert reloaded.form_data == payload


async def test_list_filters_and_pagination(
    user_factory: UserFactory,
    report_repository: SqlAlchemyReportRepository,
) -> None:
    """列表筛选、计数与分页应下推到数据库执行。"""
    user = await user_factory()
    for index in range(3):
        await report_repository.add(
            Report.create(
                report_id=_id("r"),
                ref_no=f"DAS-{uuid4().hex[:8]}",
                title=f"草稿报告-{index}",
                reporter_id=user.user_id,
                severity="P2",
            )
        )
    for index in range(2):
        report = Report.create(
            report_id=_id("r"),
            ref_no=f"DAS-{uuid4().hex[:8]}",
            title=f"待审报告-{index}",
            reporter_id=user.user_id,
            severity="P1",
        )
        report.status = ReportStatus.PENDING
        await report_repository.add(report)

    all_items, total = await report_repository.list(page=1, page_size=10)
    assert total == 5
    assert len(all_items) == 5

    drafts, draft_total = await report_repository.list(status="draft")
    assert draft_total == 3
    assert len(drafts) == 3

    severe, severe_total = await report_repository.list(severity="P1")
    assert severe_total == 2
    assert all(item.severity == "P1" for item in severe)

    first_page, _ = await report_repository.list(page=1, page_size=2)
    assert len(first_page) == 2


async def test_update_form_data_persists(
    user_factory: UserFactory,
    report_repository: SqlAlchemyReportRepository,
) -> None:
    """update_form_data 应同时落盘 form_data 与 report_data。"""
    user = await user_factory()
    saved = await report_repository.add(
        Report.create(
            report_id=_id("r"),
            ref_no=f"DAS-{uuid4().hex[:8]}",
            title="表单更新测试",
            reporter_id=user.user_id,
        )
    )

    updated = await report_repository.update_form_data(
        saved.id,
        {"manual_fault_symptom": "更新后的现象"},
        report_data={"body": {"summary": "摘要"}},
    )
    assert updated is not None

    reloaded = await report_repository.get(saved.id)
    assert reloaded is not None
    assert reloaded.form_data == {"manual_fault_symptom": "更新后的现象"}
    assert reloaded.report_data == {"body": {"summary": "摘要"}}


async def test_status_transition_persisted(
    user_factory: UserFactory,
    report_repository: SqlAlchemyReportRepository,
) -> None:
    """状态流转后的 status / verifier_id / approved_at 应真实落库。"""
    reporter = await user_factory()
    verifier = await user_factory()
    report = Report.create(
        report_id=_id("r"),
        ref_no=f"DAS-{uuid4().hex[:8]}",
        title="状态流转测试",
        reporter_id=reporter.user_id,
    )
    report.status = ReportStatus.PENDING
    saved = await report_repository.add(report)

    saved.approve(actor_id=verifier.user_id, comment=None)
    await report_repository.update(saved)

    reloaded = await report_repository.get(saved.id)
    assert reloaded is not None
    assert reloaded.status is ReportStatus.APPROVED
    assert reloaded.verifier_id == verifier.user_id
    assert reloaded.approved_at is not None


async def test_sequential_ref_no_generator_reads_max_from_database(
    db_session: AsyncSession,
    user_factory: UserFactory,
) -> None:
    """编号生成器应基于库内已有最大编号递增。"""
    user = await user_factory()
    for ref_no in ("DAS-0001", "DAS-0007"):
        await _insert_report_orm(db_session, reporter_id=user.user_id, ref_no=ref_no)

    assert await SequentialRefNoGenerator().next() == "DAS-0008"


async def test_rows_are_invisible_outside_test_transaction(
    db_engine: AsyncEngine,
    user_factory: UserFactory,
    report_repository: SqlAlchemyReportRepository,
) -> None:
    """用例内写入的行在用例事务之外不可见 —— 证明没有任何数据真正提交。"""
    user = await user_factory()
    await report_repository.add(
        Report.create(
            report_id=_id("r"),
            ref_no=f"DAS-{uuid4().hex[:8]}",
            title="隔离性验证",
            reporter_id=user.user_id,
        )
    )

    async with db_engine.connect() as outside:
        visible = await outside.scalar(select(func.count()).select_from(IncidentReport))

    assert visible == 0


async def test_database_has_no_residue_from_previous_tests(db_session: AsyncSession) -> None:
    """每个用例开始时业务表都应是干净的（前置用例已回滚）。"""
    reports = await db_session.scalar(select(func.count()).select_from(IncidentReport))
    comments = await db_session.scalar(select(func.count()).select_from(IncidentComment))

    assert reports == 0
    assert comments == 0
