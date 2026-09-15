"""「报告保存 + 预览导出」业务的真实链路回归。

为何需要这一层
--------------
在补这批用例之前，这两块业务的覆盖都是**半程**的：

* **预览**：``tests/incident_report/integration/test_preview_export_regression.py``
  用内存假仓储直接给 ``PreviewService`` 喂 ``form_data``，链路在仓储处截断。
  「填好的表单真的写进 JSONB → 原样读回 → 被 ``_build_snapshot_from_form_data``
  还原成 report_data → 渲染进 DOCX」这一段从未被真正执行。
* **保存**：``tests/incident_report/integration/test_reports_api.py`` 把整个
  ``ReportApplicationService`` 换成 ``AsyncMock``，于是 ``Report.update_fields``
  的状态守卫（仅 draft/rejected 可编辑）、``form_data`` 的替换语义、
  submit 的必填校验全部被跳过——那些用例验证的只是 HTTP 接线和 DTO 形状。

本文件把链路跑完整：HTTP → 真实 service → 真实仓储 → PostgreSQL → 渲染 DOCX/PDF。
覆盖重点是「保存进库的数据」与「导出的文档」之间的一致性，即 mock 链路测不到的部分。

隔离：每个用例跑在外层事务里，结束回滚，库中不留任何数据。
"""

from __future__ import annotations

import base64
import io
from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from docx import Document
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc_process_studio.auth.infrastructure.persistence import User
from doc_process_studio.incident_report.infrastructure.persistence import (
    IncidentAuditLog,
    IncidentReport,
)
from doc_process_studio.incident_report.infrastructure.utils.preview import (
    _PREVIEW_RESULT_CACHE,
)

pytestmark = [pytest.mark.db, pytest.mark.asyncio(loop_scope="session")]

BASE = "/api/incident-report"

# submit 前领域层会做必填校验（find_missing_submit_fields），缺一个都过不去。
SUBMIT_REQUIRED: dict[str, str] = {
    "manual_system": "DAS",
    "manual_site_id": "SITE-001",
    "manual_fault_date": "2026-09-15T09:00:00",
    "manual_reporting_person": "张三",
    "manual_fault_symptom": "收费设备离线",
}

# 表单从 22 字段扩到 33 字段，新增 Section B（清障）与 Section C（收尾）。
# 用高区分度的哨兵值，避免与模板里的静态文案偶然相等导致断言假绿。
SECTION_BC_FORM_DATA: dict[str, str] = {
    "manual_arrival_datetime": "SENTINEL-ARRIVAL-TIME",
    "manual_clearance_datetime": "SENTINEL-CLEARANCE-TIME",
    "manual_service_person": "SENTINEL-SERVICE-PERSON",
    "manual_fault_cause": "SENTINEL-FAULT-CAUSE",
    "manual_materials_used": "SENTINEL-MATERIALS-USED",
    "manual_repair_details": "SENTINEL-REPAIR-DETAILS",
    "manual_contractor_staff": "SENTINEL-CONTRACTOR-STAFF",
    "manual_contractor_signature": "SENTINEL-CONTRACTOR-SIGN",
    "manual_contractor_date": "SENTINEL-CONTRACTOR-DATE",
    "manual_comments": "SENTINEL-CLOSEOUT-COMMENTS",
    "manual_employer_rep": "SENTINEL-EMPLOYER-REP",
    "manual_employer_signature": "SENTINEL-EMPLOYER-SIGN",
    "manual_closeout_date": "SENTINEL-CLOSEOUT-DATE",
}

RegisterUserFactory = Callable[..., Coroutine[Any, Any, User]]
RowCounter = Callable[..., Coroutine[Any, Any, int]]
TokenFactory = Callable[[User], dict[str, str]]


@pytest.fixture(autouse=True)
def _clear_preview_cache() -> object:
    """预览结果是进程级 LRU 缓存，跨用例不清会读到上一个事务的内容。"""
    _PREVIEW_RESULT_CACHE.clear()
    yield
    _PREVIEW_RESULT_CACHE.clear()


async def _create_report(
    client: AsyncClient,
    token_headers: TokenFactory,
    user: User,
    *,
    title: str = "保存与预览回归",
    form_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(SUBMIT_REQUIRED)
    merged.update(form_data or {})
    response = await client.post(
        f"{BASE}/reports",
        headers=token_headers(user),
        json={"title": title, "form_data": merged},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


async def _persisted_form_data(session: AsyncSession, report_id: str) -> dict[str, Any]:
    """绕开任何业务缓存，直接读库里的 JSONB 列。"""
    value = (await session.execute(select(IncidentReport.form_data).where(IncidentReport.id == report_id))).scalar_one()
    return dict(value or {})


async def _persisted_status(session: AsyncSession, report_id: str) -> str:
    status = (await session.execute(select(IncidentReport.status).where(IncidentReport.id == report_id))).scalar_one()
    return str(status)


def _docx_text(docx_base64: str) -> str:
    """提取 DOCX 全部可见文本（段落 + 表格单元格）。"""
    document = Document(io.BytesIO(base64.b64decode(docx_base64)))
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


async def _preview(
    client: AsyncClient,
    token_headers: TokenFactory,
    user: User,
    report_id: str,
) -> dict[str, Any]:
    response = await client.post(
        f"{BASE}/reports/{report_id}/preview",
        headers=token_headers(user),
        json={},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


# ---------------------------------------------------------------- 保存：更新语义


async def test_put_replaces_form_data_wholesale(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    db_session: AsyncSession,
) -> None:
    """PUT 的 form_data 是**整体替换**而非按 key 合并——固化这个容易被误读的行为。

    路由层 ``model_dump`` 过滤掉 None 后把整个 dict 交给 ``update_fields``，
    后者执行 ``setattr``。因此前端保存时必须回传完整表单，
    只传增量会把未提交的字段从库里抹掉。
    """
    user = await register_user()
    created = await _create_report(
        api_client,
        token_headers,
        user,
        form_data={"body": {"summary": "初始摘要"}, "manual_fault_cause": "初始故障原因"},
    )

    update_resp = await api_client.put(
        f"{BASE}/reports/{created['id']}",
        headers=token_headers(user),
        json={"form_data": {"manual_fault_cause": "更新后的故障原因"}},
    )
    assert update_resp.status_code == 200, update_resp.text

    persisted = await _persisted_form_data(db_session, created["id"])
    assert persisted["manual_fault_cause"] == "更新后的故障原因"
    assert "body" not in persisted, "PUT 是整体替换：未回传的字段会被清除，而非保留"


async def test_put_omitted_fields_are_ignored(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    db_session: AsyncSession,
) -> None:
    """body 里省略的字段保持原值（None 被过滤，不参与写入）。"""
    user = await register_user()
    created = await _create_report(
        api_client,
        token_headers,
        user,
        title="原始标题",
        form_data={"manual_fault_cause": "不应被覆盖"},
    )

    update_resp = await api_client.put(
        f"{BASE}/reports/{created['id']}",
        headers=token_headers(user),
        json={"title": "更新后的标题"},
    )
    assert update_resp.status_code == 200, update_resp.text

    row = (
        await db_session.execute(
            select(IncidentReport.title, IncidentReport.form_data).where(IncidentReport.id == created["id"])
        )
    ).one()
    title, form_data = row
    assert title == "更新后的标题"
    assert dict(form_data)["manual_fault_cause"] == "不应被覆盖"


async def test_put_rejected_after_submit(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    db_session: AsyncSession,
) -> None:
    """已提交的报告不可再编辑：update_fields 的状态守卫必须拦住。"""
    user = await register_user()
    created = await _create_report(api_client, token_headers, user, title="待提交")

    submit_resp = await api_client.post(
        f"{BASE}/reports/{created['id']}/submit",
        headers=token_headers(user),
    )
    assert submit_resp.status_code == 200, submit_resp.text

    update_resp = await api_client.put(
        f"{BASE}/reports/{created['id']}",
        headers=token_headers(user),
        json={"title": "提交后试图改名"},
    )
    assert update_resp.status_code == 400, "pending 状态下的编辑应被领域层拒绝"

    title = (
        await db_session.execute(select(IncidentReport.title).where(IncidentReport.id == created["id"]))
    ).scalar_one()
    assert title == "待提交", "被拒绝的编辑不能污染库里的值"


async def test_rejected_report_becomes_editable_again(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    db_session: AsyncSession,
) -> None:
    """驳回回到 rejected 后重新可编辑——与上面那条构成一对完整守卫。"""
    reporter = await register_user()
    verifier = await register_user(role="verifier")
    created = await _create_report(api_client, token_headers, reporter, title="将被驳回")

    submit_resp = await api_client.post(
        f"{BASE}/reports/{created['id']}/submit",
        headers=token_headers(reporter),
    )
    assert submit_resp.status_code == 200, submit_resp.text

    reject_resp = await api_client.post(
        f"{BASE}/reports/{created['id']}/reject",
        headers=token_headers(verifier),
        json={"comment": "材料不全，请补充"},
    )
    assert reject_resp.status_code == 200, reject_resp.text
    assert await _persisted_status(db_session, created["id"]) == "rejected"

    update_resp = await api_client.put(
        f"{BASE}/reports/{created['id']}",
        headers=token_headers(reporter),
        json={"form_data": dict(SUBMIT_REQUIRED, manual_fault_cause="补充后的原因")},
    )
    assert update_resp.status_code == 200, update_resp.text

    persisted = await _persisted_form_data(db_session, created["id"])
    assert persisted["manual_fault_cause"] == "补充后的原因"


# ---------------------------------------------------------------- 保存：状态流转


async def test_full_workflow_persists_every_transition(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    count_rows_helper: RowCounter,
    db_session: AsyncSession,
) -> None:
    """submit → approve → close 全流程：每一步都要落库，且都要写审计。"""
    reporter = await register_user()
    verifier = await register_user(role="verifier")
    handler = await register_user(role="handler")
    created = await _create_report(api_client, token_headers, reporter, title="全流程报告")
    report_id = created["id"]

    await _expect_ok(api_client.post(f"{BASE}/reports/{report_id}/submit", headers=token_headers(reporter)))
    assert await _persisted_status(db_session, report_id) == "pending"

    await _expect_ok(
        api_client.post(
            f"{BASE}/reports/{report_id}/approve",
            headers=token_headers(verifier),
            json={"comment": "通过"},
        )
    )
    assert await _persisted_status(db_session, report_id) == "approved"

    await _expect_ok(
        api_client.post(
            f"{BASE}/reports/{report_id}/assign",
            headers=token_headers(verifier),
            json={"assignee_id": handler.user_id},
        )
    )
    assignee = (
        await db_session.execute(select(IncidentReport.assignee_id).where(IncidentReport.id == report_id))
    ).scalar_one()
    assert assignee == handler.user_id

    await _expect_ok(
        api_client.post(
            f"{BASE}/reports/{report_id}/close",
            headers=token_headers(handler),
            json={"comment": "处理完成"},
        )
    )
    row = (
        await db_session.execute(
            select(IncidentReport.status, IncidentReport.closed_at).where(IncidentReport.id == report_id)
        )
    ).one()
    status, closed_at = row
    assert str(status) == "closed"
    assert closed_at is not None, "关闭时间必须真的写进列，不能只停在 DTO 里"

    audit_count = await count_rows_helper(db_session, IncidentAuditLog, report_id=report_id)
    assert audit_count >= 4, f"四次流转应各留一条审计，实际 {audit_count}"


async def test_submit_requires_business_fields(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    db_session: AsyncSession,
) -> None:
    """缺必填项时 submit 必须失败，且状态不能从 draft 变化。"""
    user = await register_user()
    response = await api_client.post(
        f"{BASE}/reports",
        headers=token_headers(user),
        json={"title": "缺字段报告", "form_data": {"manual_system": "DAS"}},
    )
    assert response.status_code == 200, response.text
    report_id = response.json()["id"]

    submit_resp = await api_client.post(
        f"{BASE}/reports/{report_id}/submit",
        headers=token_headers(user),
    )
    assert submit_resp.status_code == 400, "必填项缺失时应被领域层拒绝"
    assert await _persisted_status(db_session, report_id) == "draft"


async def test_ref_no_taken_from_form_data(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    db_session: AsyncSession,
) -> None:
    """ref_no 取值优先级：显式入参 > form_data.manual_reference_no > 自动生成。"""
    user = await register_user()
    created = await _create_report(
        api_client,
        token_headers,
        user,
        form_data={"manual_reference_no": "REF-FROM-FORM-001"},
    )

    assert created["ref_no"] == "REF-FROM-FORM-001"
    ref_no = (
        await db_session.execute(select(IncidentReport.ref_no).where(IncidentReport.id == created["id"]))
    ).scalar_one()
    assert ref_no == "REF-FROM-FORM-001"


# ---------------------------------------------------------------- 预览：真实库 → 文档


async def test_preview_renders_form_data_read_back_from_database(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    db_session: AsyncSession,
) -> None:
    """核心断言：库里读出来的 JSONB 能还原进 DOCX。

    这条链路在纯 mock 测试里永远测不到——假仓储直接给服务喂 Python dict，
    跳过了 JSONB 序列化往返与 ``_build_snapshot_from_form_data`` 还原。
    """
    user = await register_user()
    created = await _create_report(
        api_client,
        token_headers,
        user,
        # 注意：form_data 是**扁平**字典，正文段落用 body_* 前缀，不是嵌套的 {"body": {...}}
        form_data=dict(SECTION_BC_FORM_DATA, body_description="持久化后的中文摘要"),
    )

    # 先确认数据确实落到了 JSONB 里（中间产物可观测）
    persisted = await _persisted_form_data(db_session, created["id"])
    assert persisted["manual_service_person"] == "SENTINEL-SERVICE-PERSON"
    assert persisted["body_description"] == "持久化后的中文摘要"

    preview = await _preview(api_client, token_headers, user, created["id"])
    assert preview["docx_base64"], "预览必须产出 DOCX"
    text = _docx_text(preview["docx_base64"])

    assert "持久化后的中文摘要" in text
    for field_value in SECTION_BC_FORM_DATA.values():
        assert field_value in text, f"{field_value} 未渲染进导出文档"
    assert preview["warnings"] == [], f"预览不应带警告：{preview['warnings']}"


async def test_preview_reflects_latest_saved_value(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
    db_session: AsyncSession,
) -> None:
    """改了就导出最新：验证预览结果跟着库里的数据走，没有被缓存串台。"""
    user = await register_user()
    created = await _create_report(
        api_client,
        token_headers,
        user,
        form_data={"manual_fault_cause": "初次填写的故障原因"},
    )
    report_id = created["id"]

    first_text = _docx_text((await _preview(api_client, token_headers, user, report_id))["docx_base64"])
    assert "初次填写的故障原因" in first_text

    await api_client.put(
        f"{BASE}/reports/{report_id}",
        headers=token_headers(user),
        json={"form_data": dict(SUBMIT_REQUIRED, manual_fault_cause="修订后的故障原因")},
    )
    # 先确认新值真的进了库，再确认按钮了导出——两步分开才能定位是保存还是渲染的问题
    persisted = await _persisted_form_data(db_session, report_id)
    assert persisted["manual_fault_cause"] == "修订后的故障原因"

    second_text = _docx_text((await _preview(api_client, token_headers, user, report_id))["docx_base64"])

    assert "修订后的故障原因" in second_text
    assert "初次填写的故障原因" not in second_text, "预览应反映库中的最新值"


async def test_pdf_preview_generated_without_warning(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
) -> None:
    """PDF 分支依赖外部 LibreOffice。失败不会抛异常、只写进 warnings，必须显式断言。"""
    user = await register_user()
    created = await _create_report(api_client, token_headers, user)

    preview = await _preview(api_client, token_headers, user, created["id"])
    assert preview["warnings"] == [], f"PDF 生成失败只体现在 warnings 里：{preview['warnings']}"
    assert preview["pdf_base64"], "LibreOffice 可用时应产出 PDF"


async def test_preview_denied_for_unrelated_user(
    api_client: AsyncClient,
    register_user: RegisterUserFactory,
    token_headers: TokenFactory,
) -> None:
    """无 report:view_all 且未参与报告的用户，预览必须被拒。"""
    reporter = await register_user()
    outsider = await register_user(role="viewer")
    created = await _create_report(api_client, token_headers, reporter)

    response = await api_client.post(
        f"{BASE}/reports/{created['id']}/preview",
        headers=token_headers(outsider),
        json={},
    )
    assert response.status_code == 403


async def _expect_ok(coroutine: Coroutine[Any, Any, Any]) -> dict[str, Any]:
    """断言一次写操作成功，失败时把响应体带出来便于定位。"""
    response = await coroutine
    assert response.status_code == 200, response.text
    return dict(response.json())
