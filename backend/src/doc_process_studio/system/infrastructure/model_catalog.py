"""Ollama 模型目录实现。

实现 ModelCatalog 端口，委托 core/ollama 的 fetch_remote_model_names。
"""

from ...common.infrastructure.ollama import fetch_remote_model_names
from ..application.ports import ModelCatalog


class OllamaModelCatalog(ModelCatalog):
    """基于 Ollama 的模型目录。"""

    async def list_remote_model_names(self) -> list[str]:
        return await fetch_remote_model_names()
