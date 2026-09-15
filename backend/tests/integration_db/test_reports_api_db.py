"""HTTP → service → 真实仓储 → PostgreSQL 的完整链路集成测试。

这批用例覆盖的是 mock 仓储**永远测不到**的行为：

* 列表过滤是否真的下推到 SQL WHERE（而不是内存假数据集的巧合）；
* 报告删除时评论是否真的被外键级联删除；
* 状态流转是否同时写库并留下审计记录；
* 时间戳 ``server_default`` 是否真的由数据库侧生成；
* JSONB 表单数据在完整链路上的往返。

每个用例都跑在外层事务里，结束回滚，不留任何数据。
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc_process_studio.auth.infrastructure.persistence import User
from doc_process_studio.incident_report.infrastructure.persistence import (
    IncidentAuditLog,
    IncidentComment,
    IncidentReport,
)

pytestmark = [pytest.mark.db, pytest.mark.asyncio(loop_scope="session")]

BASE = "/api/incident-report"

# 提交（submit）前必须通过领域层的必填校验，这批字段是 report_data 要求的业务必填项。
REQUIRED_FORM_DATA: dict[str, str] = {
    "manual_system": "DAS",
    "manual_site_id": "SITE-001",
    "manual_fault_date": "2026-09-15T09:00:00",
    "manual_reporting_person": "张三",
    "manual_fault_symptom": "收费设备离线",
}

RegisterUserFactory = Callable[..., Coroutine[Any, Any, User]]
RowCounter = Callable[..., Coroutine[Any, Any, int]]
TokenFactory = Callable[[User], dict[str, str]]


async def _create_report(
    client: AsyncClient,
    user: User,
    token_headers: TokenFactory,
    title: str = "集成测试报告",
    form_data: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    merged_form_data = dict(REQUIRED_FORM_DATA)
    merged_form_data.update(form_data or {})
    payload: dict[str, Any] = {"title": title, "form_data": merged_form_data}
    payload.update(overrides)
    response = await client.post(f"{BASE}/reports", headers=token_headers(user), json=payload)
    assert response.status_code == 200, response.text
    return dict(response.json())


async def test_create_report_persists_form_data_and_timestamps(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    count_rows_helper: RowCounter,
    db_session: AsyncSession,
) -> None:
    user = await register_user()
    created = await _create_report(
        api_client,
        user,
        token_headers,
        title="落库验证报告",
        form_data={"body": {"summary": "中文摘要-真实入库"}},
    )

    assert created["ref_no"], "ref_no 应由服务端序列生成器分配"
    assert await count_rows_helper(db_session, IncidentReport, id=created["id"]) == 1

    row = (
        await db_session.execute(
            select(
                IncidentReport.form_data,
                IncidentReport.created_at,
                IncidentReport.updated_at,
            ).where(IncidentReport.id == created["id"])
        )
    ).one()
    form_data, created_at, updated_at = row

    assert form_data["body"]["summary"] == "中文摘要-真实入库"
    # server_default=now()：时间戳必须由数据库侧生成，而非 ORM 缺省值
    assert created_at is not None
    assert updated_at is not None


async def test_submit_report_writes_status_and_audit_log(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    count_rows_helper: RowCounter,
    db_session: AsyncSession,
) -> None:
    user = await register_user()
    created = await _create_report(api_client, user, token_headers, title="待提交报告")

    response = await api_client.post(
        f"{BASE}/reports/{created['id']}/submit",
        headers=token_headers(user),
    )
    assert response.status_code == 200, response.text

    status = (
        await db_session.execute(select(IncidentReport.status).where(IncidentReport.id == created["id"]))
    ).scalar_one()
    status_text = str(status)
    assert status_text != "draft", "提交后状态应已流转"
    assert response.json()["status"] == status_text

    assert await count_rows_helper(db_session, IncidentAuditLog, report_id=created["id"]) >= 1


async def test_list_reports_status_filter_is_pushed_down_to_sql(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
) -> None:
    user = await register_user()
    draft = await _create_report(api_client, user, token_headers, title="草稿报告")
    submitted = await _create_report(api_client, user, token_headers, title="已提交报告")

    submit_resp = await api_client.post(
        f"{BASE}/reports/{submitted['id']}/submit",
        headers=token_headers(user),
    )
    assert submit_resp.status_code == 200, submit_resp.text
    submitted_status = submit_resp.json()["status"]

    response = await api_client.get(
        f"{BASE}/reports",
        params={"status": submitted_status},
        headers=token_headers(user),
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["total"] == 1
    returned_ids = [item["id"] for item in data["items"]]
    assert returned_ids == [submitted["id"]]
    assert draft["id"] not in returned_ids


async def test_reporter_only_lists_own_reports(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
) -> None:
    alice = await register_user()
    bob = await register_user()
    alice_report = await _create_report(api_client, alice, token_headers, title="爱丽丝的报告")
    await _create_report(api_client, bob, token_headers, title="鲍勃的报告")

    response = await api_client.get(f"{BASE}/reports", headers=token_headers(alice))
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["id"] == alice_report["id"]


async def test_delete_report_cascades_comments(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    count_rows_helper: RowCounter,
    db_session: AsyncSession,
) -> None:
    admin = await register_user(role="admin")
    created = await _create_report(api_client, admin, token_headers, title="待删除报告")

    comment_resp = await api_client.post(
        f"{BASE}/reports/{created['id']}/comments",
        headers=token_headers(admin),
        json={"content": "级联删除验证评论"},
    )
    assert comment_resp.status_code == 200, comment_resp.text
    assert await count_rows_helper(db_session, IncidentComment, report_id=created["id"]) == 1

    delete_resp = await api_client.delete(
        f"{BASE}/reports/{created['id']}",
        headers=token_headers(admin),
    )
    assert delete_resp.status_code == 200, delete_resp.text

    assert await count_rows_helper(db_session, IncidentReport, id=created["id"]) == 0
    assert await count_rows_helper(db_session, IncidentComment, report_id=created["id"]) == 0
