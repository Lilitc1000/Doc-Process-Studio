"""报告正文生成应用服务。

包装 service/generation.py 的生成逻辑，通过依赖注入暴露给 router。
权限检查保留在底层实现中，本层仅做编排。
"""

from ..schemas.response import IncidentBodyGenerateResponse


class GenerationService:
    """报告正文生成用例：快速生成 + 分段生成。"""

    async def quick_generate(
        self,
        *,
        report_id: str,
        user_id: str,
        model: str | None = None,
        reranker_model: str | None = None,
    ) -> IncidentBodyGenerateResponse:
        from ..service.generation import quick_generate_report_body

        return await quick_generate_report_body(
            report_id=report_id,
            user_id=user_id,
            model=model,
            reranker_model=reranker_model,
        )

    async def generate_section(
        self,
        *,
        report_id: str,
        section_id: str,
        timeline_index: int | None = None,
        user_id: str,
        model: str | None = None,
        reranker_model: str | None = None,
    ) -> IncidentBodyGenerateResponse:
        from ..service.generation import generate_report_body_section

        return await generate_report_body_section(
            report_id=report_id,
            section_id=section_id,
            timeline_index=timeline_index,
            user_id=user_id,
            model=model,
            reranker_model=reranker_model,
        )
