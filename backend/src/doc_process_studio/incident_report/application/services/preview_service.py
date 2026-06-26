"""报告预览应用服务。

编排预览生成的用例：加载报告 → 权限检查 → 构建数据 →
渲染 DOCX/PDF → 缓存 → 返回。
所有跨域调用通过端口抽象，不直接依赖 service 层和外部域。
"""

import base64
import logging

from ...domain.values.errors import PermissionDeniedError
from ...domain.values.permission import Permission
from ..dtos import IncidentReportPreviewResponse
from ..ports import PermissionChecker, ReportRepository

logger = logging.getLogger(__name__)


class PreviewService:
    """报告预览用例：生成 DOCX/PDF 预览。"""

    def __init__(
        self,
        repo: ReportRepository,
        checker: PermissionChecker,
    ) -> None:
        self._repo = repo
        self._checker = checker

    async def preview_report(
        self,
        *,
        report_id: str,
        user_id: str,
        version: int | None = None,
        model: str | None = None,
        reranker_model: str | None = None,
    ) -> IncidentReportPreviewResponse:
        report = await self._repo.get(report_id)
        if report is None:
            raise ValueError(f"Report {report_id} does not exist.")

        # 权限检查
        perms = await self._checker.permissions_of(user_id)
        can_view = (
            report.reporter_id == user_id
            or report.assignee_id == user_id
            or report.verifier_id == user_id
            or Permission.REPORT_VIEW_ALL in perms
        )
        if not can_view:
            raise PermissionDeniedError("无权预览此报告")

        from ...infrastructure.utils.generation import _build_snapshot_from_form_data
        from ...infrastructure.utils.normalization import normalize_text
        from ...infrastructure.utils.preview import (
            build_preview_output_name,
            convert_docx_bytes_to_pdf_bytes,
            preview_cache_get,
            preview_cache_set,
            preview_template_token,
            render_docx_bytes_from_report_data,
        )
        from ...infrastructure.utils.report_data import build_report_data_from_snapshot

        snapshot = _build_snapshot_from_form_data(report.form_data)
        report_data, missing = build_report_data_from_snapshot(
            snapshot,
            strict_required=False,
        )
        if report_data is None:
            report_data = {"missing_fields": missing}

        preview_model = normalize_text(model) or normalize_text(reranker_model)
        from ...infrastructure.utils.preview import _stable_payload_hash

        draft_hash = _stable_payload_hash(report_data)
        cache_key = f"report:{report_id}:v{version or 'draft'}:{preview_model}:{preview_template_token()}:{draft_hash}"
        cached = preview_cache_get(cache_key)
        if cached is not None:
            return cached

        docx_bytes = render_docx_bytes_from_report_data(report_data)

        warnings: list[str] = []
        pdf_base64: str | None = None
        try:
            pdf_bytes = convert_docx_bytes_to_pdf_bytes(docx_bytes)
            pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
        except Exception as exc:
            warnings.append(f"PDF preview generation failed: {normalize_text(exc)}")

        output_name = build_preview_output_name(
            report_title=report.title,
            report_id=report_id,
        )

        response = IncidentReportPreviewResponse(
            source="draft",
            version=version,
            label=output_name.replace(".docx", ""),
            html="",
            docx_base64=base64.b64encode(docx_bytes).decode("ascii"),
            docx_file_name=output_name,
            pdf_base64=pdf_base64,
            warnings=warnings,
        )

        preview_cache_set(cache_key=cache_key, payload=response)
        return response
