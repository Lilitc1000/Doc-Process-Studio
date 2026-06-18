"""系统应用层端口。

定义数据访问和外部服务抽象，由 infrastructure 层实现。
"""

from abc import ABC, abstractmethod
from typing import Any


class TraceStore(ABC):
    """Agent trace 存储端口。"""

    @abstractmethod
    async def load(self, *, tenant_id: str, trace_id: str) -> dict[str, Any] | None:
        """按 tenant_id + trace_id 加载 trace 负载，不存在返回 None。"""


class ModelCatalog(ABC):
    """模型目录端口。"""

    @abstractmethod
    async def list_remote_model_names(self) -> list[str]:
        """获取远端可用模型名列表。"""
