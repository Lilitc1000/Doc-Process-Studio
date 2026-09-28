"""RAGFlow 知识库列表实现。

复用 :class:`RagflowClient` 的 ``list_datasets``，与连通性自检走同一条读路径 ——
避免"设置页能看到、实际检索却访问不到"这种两套判断标准的问题。
"""

from __future__ import annotations

from ...knowledge_base.infrastructure.ragflow_client import RagflowClient
from ..application.ports import RagflowDatasetCatalog, RagflowDatasetInfo
from ..domain.values import RagflowConfig


def _to_int(value: object) -> int:
    """把 RAGFlow 返回的计数宽容地转成 int；取不到就当 0。"""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


class RagflowClientDatasetCatalog(RagflowDatasetCatalog):
    """用当前生效凭据调 ``GET /api/v1/datasets`` 取知识库列表。

    超时取自当前生效配置（``config.timeout_seconds``），不再依赖环境变量。
    """

    def __init__(self, *, timeout_seconds: float | None = None) -> None:
        self._fallback_timeout = timeout_seconds

    async def list_datasets(self, config: RagflowConfig) -> list[RagflowDatasetInfo]:
        if not config.usable:
            return []

        client = RagflowClient(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds if config.timeout_seconds is not None else self._fallback_timeout,
        )
        raw_items = await client.list_datasets()

        results: list[RagflowDatasetInfo] = []
        for item in raw_items:
            dataset_id = str(item.get("id") or "").strip()
            if not dataset_id:
                continue
            name = str(item.get("name") or dataset_id).strip()
            results.append(
                RagflowDatasetInfo(
                    id=dataset_id,
                    name=name,
                    document_count=_to_int(item.get("document_count")),
                    chunk_count=_to_int(item.get("chunk_count")),
                    language=str(item.get("language") or ""),
                )
            )
        results.sort(key=lambda ds: ds.name.lower())
        return results
