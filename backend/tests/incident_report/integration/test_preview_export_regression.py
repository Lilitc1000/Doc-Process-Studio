"""回归：DAS2 表单新增字段必须出现在导出文档中。

背景
----
表单 Schema 从 4 步 22 字段扩充到 6 步 33 字段（新增 `clearance` 9 个、
`closeout` 5 个字段）。此前「Section B/C 的值能否正确渲染进 DOCX/PDF」只能靠
人工打开预览确认，本测试把它自动化。

为何不需要浏览器或数据库
------------------------
`PreviewService.preview_report()` 只依赖 `ReportRepository` 与
`PermissionChecker` 两个端口，输入就是 `report.form_data`，返回
`docx_base64` / `pdf_base64` / `warnings`。因此用内存假实现即可驱动完整渲染
链路，无需 Starts 真实数据库、HTTP 服务或浏览器。

注意点
------
PDF 分支依赖外部 LibreOffice（`soffice` 命令），缺失时自动跳过；且 PDF 生成
失败**不会抛异常**，只会往 `warnings` 里追加一句，所以必须显式断言
`warnings == []`，否则 PDF 坏了也无人察觉。
"""

from __future__ import annotations

import base64
import io
import shutil
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from docx import Document

from doc_process_studio.incident_report.application.ports import (
    PermissionChecker,
    ReportRepository,
)
from doc_process_studio.incident_report.application.services.preview_service import (
    PreviewService,
)
from doc_process_studio.incident_report.domain.entities.report import Report
from doc_process_studio.incident_report.domain.entities.status import ReportStatus
from doc_process_studio.incident_report.domain.values.permission import Permission
from doc_process_studio.incident_report.infrastructure.utils.preview import (
    _PREVIEW_RESULT_CACHE,
)

_REPORT_ID = "rep-export-regression"
_USER_ID = "usr-export-regression"

# 新增的 clearance(Section B) / closeout(Section C) 字段的期望渲染值。
_NEW_FIELDS_EXPECTED: dict[str, str] = {
    "manual_arrival_datetime": "18:30, 12/03/2026",
    "manual_clearance_datetime": "02:15, 13/03/2026",
    "manual_service_person": "REG-SERVICE-PERSON",
    "manual_fault_cause": "REG-FAULT-CAUSE",
    "manual_materials_used": "REG-MATERIALS-USED",
    "manual_repair_details": "REG-REPAIR-DETAILS",
    "manual_contractor_staff": "REG-CONTRACTOR-STAFF",
    "manual_contractor_signature": "REG-CONTRACTOR-SIGN",
    "manual_contractor_date": "REG-CONTRACTOR-DATE",
    "manual_comments": "REG-CLOSEOUT-COMMENTS",
    "manual_employer_rep": "REG-EMPLOYER-REP",
    "manual_employer_signature": "REG-EMPLOYER-SIGN",
    "manual_closeout_date": "REG-CLOSEOUT-DATE",
}


def _full_form_data() -> dict[str, Any]:
    """构造一份填满的表单数据。

    这里用的是**前端实际写入的 form key**，而不是 Schema 的 `field_id`
    （两者在个别字段上不一致，见 test_schema_export_field_consistency.py）。
    """
    return {
        "manual_reference_no": "REG-REF-001",
        "manual_fault_date": "2026-03-12",
        "manual_fault_time": "17:07",
        "manual_reporting_person": "REG-REPORTER",
        "manual_verified_by": "REG-VERIFIER",
        "manual_site_id": "SITE-REG-001",
        "manual_system": "DAS",
        "manual_location": "REG-LOCATION",
        "manual_fault_symptom": "REG-SYMPTOM",
        "manual_status": "fault_cleared",
        "manual_status_ref_no": "WO-REG-7788",
        "manual_severity": "major",
        # Section B（新增 clearance）
        **_NEW_FIELDS_EXPECTED,
        # 正文与附录
        "body_description": "REG-DESCRIPTION",
        "body_impact_scope": "REG-IMPACT-SCOPE",
        "body_impact_severity": "major",
        "body_root_cause": "REG-ROOT-CAUSE",
        "body_follow_up": "REG-FOLLOW-UP",
        "body_timeline": [
            {"time": "17:07", "event": "REG-TIMELINE-ONE"},
            {"time": "18:30", "event": "REG-TIMELINE-TWO"},
        ],
        "appendix_notes": "REG-APPENDIX-NOTES",
    }


class _FakeReportRepository:
    """只实现 PreviewService 用到的 get()，用 cast 满足端口类型。"""

    def __init__(self, report: Report) -> None:
        self._report = report

    async def get(self, report_id: str) -> Report | None:
        return self._report if report_id == self._report.id else None


class _FakePermissionChecker:
    """按 user_id 决定是否放行，顺带覆盖权限分支。"""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id

    async def permissions_of(self, user_id: str) -> set[Permission]:
        return {Permission.REPORT_VIEW_ALL} if user_id == self._user_id else set()


def _build_report() -> Report:
    now = datetime.now(UTC)
    return Report(
        id=_REPORT_ID,
        ref_no="REG-REF-001",
        title="导出回归报告",
        status=ReportStatus.DRAFT,
        reporter_id=_USER_ID,
        severity=None,
        system="DAS",
        site_id="SITE-REG-001",
        fault_date=now,
        form_data=_full_form_data(),
    )


def _make_service() -> PreviewService:
    repo = cast(ReportRepository, _FakeReportRepository(_build_report()))
    checker = cast(PermissionChecker, _FakePermissionChecker(_USER_ID))
    return PreviewService(repo=repo, checker=checker)


def _docx_text(docx_bytes: bytes) -> str:
    """提取 DOCX 的全部可见文本（段落 + 表格）。"""
    document = Document(io.BytesIO(docx_bytes))
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


@pytest.fixture(autouse=True)
def _isolated_preview_cache() -> Generator[None]:
    """预览结果有进程级 LRU 缓存，必须隔离，否则跨用例污染。"""
    _PREVIEW_RESULT_CACHE.clear()
    yield
    _PREVIEW_RESULT_CACHE.clear()


async def test_new_das2_fields_render_into_docx() -> None:
    response = await _make_service().preview_report(
        report_id=_REPORT_ID,
        user_id=_USER_ID,
    )

    assert response.warnings == [], f"预览生成出现警告：{response.warnings}"
    assert response.docx_base64, "未返回 DOCX 内容"

    text = _docx_text(base64.b64decode(response.docx_base64))
    missing = [f"{field_id}={value}" for field_id, value in _NEW_FIELDS_EXPECTED.items() if value not in text]
    assert missing == [], f"以下新增字段未出现在导出文档中：{missing}"


async def test_core_identity_fields_render_into_docx() -> None:
    """确保新增内容没有挤掉原有字段（回归而非只测新功能）。"""
    response = await _make_service().preview_report(
        report_id=_REPORT_ID,
        user_id=_USER_ID,
    )
    text = _docx_text(base64.b64decode(response.docx_base64 or ""))

    expected = [
        "REG-REPORTER",
        "REG-SYMPTOM",
        "SITE-REG-001",
        "REG-DESCRIPTION",
        "REG-ROOT-CAUSE",
        "REG-APPENDIX-NOTES",
    ]
    missing = [item for item in expected if item not in text]
    assert missing == [], f"原有字段在导出文档中丢失：{missing}"


@pytest.mark.skipif(
    shutil.which("soffice") is None,
    reason="PDF 预览依赖外部 LibreOffice（soffice），当前环境缺失",
)
async def test_pdf_preview_generated_without_warning() -> None:
    response = await _make_service().preview_report(
        report_id=_REPORT_ID,
        user_id=_USER_ID,
    )

    assert response.warnings == [], f"PDF 预览出现警告：{response.warnings}"
    assert response.pdf_base64, "未返回 PDF 内容"


async def test_pdf_failure_is_surfaced_as_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PDF 失败只进 warnings、不抛异常，必须能被观测到。

    这条用例守护的是「静默失败」风险：若哪天把异常吞掉又不写 warnings，
    用户会拿到没有警告的空 PDF。
    """

    def _boom(*_args: Any, **_kwargs: Any) -> bytes:
        raise RuntimeError("soffice unavailable in test")

    monkeypatch.setattr(
        "doc_process_studio.incident_report.infrastructure.utils.preview.convert_docx_bytes_to_pdf_bytes",
        _boom,
    )

    response = await _make_service().preview_report(
        report_id=_REPORT_ID,
        user_id=_USER_ID,
    )

    assert response.pdf_base64 is None
    assert response.warnings, "PDF 失败未写入 warnings，属于静默失败"
    assert any("soffice unavailable" in item for item in response.warnings)


async def test_permission_denied_for_unrelated_user() -> None:
    """顺带覆盖权限分支：非相关用户不得预览。"""
    from doc_process_studio.incident_report.domain.values.errors import (
        PermissionDeniedError,
    )

    with pytest.raises(PermissionDeniedError):
        await _make_service().preview_report(
            report_id=_REPORT_ID,
            user_id="usr-someone-else",
        )
