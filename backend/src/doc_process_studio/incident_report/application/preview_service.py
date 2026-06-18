"""报告预览应用服务。

包装 service/preview.py 的预览逻辑，通过依赖注入暴露给 router。
权限检查保留在底层实现中，本层仅做编排。
"""

from ..schemas.response import IncidentReportPreviewResponse


class PreviewService:
    """报告预览用例：生成 DOCX/PDF 预览。"""

    async def preview_report(
        self,
        *,
        report_id: str,
        user_id: str,
        version: int | None = None,
        model: str | None = None,
        reranker_model: str | None = None,
    ) -> IncidentReportPreviewResponse:
        from ..service.preview import preview_report_attachment

        return await preview_report_attachment(
            report_id=report_id,
            user_id=user_id,
            version=version,
            model=model,
            reranker_model=reranker_model,
        )
