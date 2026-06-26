"""系统应用服务契约。

定义应用服务对外暴露的调用接口，测试桩类继承此契约以确保签名同步。
运行时实例化桩类会自动检测未实现的抽象方法。
"""

from abc import ABC, abstractmethod
from typing import Any


class TraceQueryServiceContract(ABC):
    """Agent trace 查询用例服务契约。"""

    @abstractmethod
    async def get_trace(self, *, tenant_id: str, trace_id: str) -> dict[str, Any]: ...


class ModelQueryServiceContract(ABC):
    """模型列表查询用例服务契约。"""

    @abstractmethod
    async def list_remote_models(self) -> list[str]: ...
