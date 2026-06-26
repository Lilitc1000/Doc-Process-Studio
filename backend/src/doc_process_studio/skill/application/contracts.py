"""技能应用服务契约。

定义应用服务对外暴露的调用接口，测试桩类继承此契约以确保签名同步。
运行时实例化桩类会自动检测未实现的抽象方法。
"""

from abc import ABC, abstractmethod

from .dtos.catalog import SkillInterfaceConfig
from .dtos.runtime import SkillContextChunk


class SkillServiceContract(ABC):
    """技能用例服务契约。"""

    @abstractmethod
    def list_skills(self) -> list[SkillInterfaceConfig]: ...

    @abstractmethod
    async def search_context(self, skill_id: str, query: str) -> list[SkillContextChunk]: ...

    @abstractmethod
    async def refresh_conversation_cache(
        self,
        conversation_id: str,
        tenant_id: str = "default",
    ) -> tuple[bool, int]: ...

    @abstractmethod
    async def delete_conversation_cache(
        self,
        conversation_id: str,
        tenant_id: str = "default",
    ) -> tuple[bool, int]: ...
