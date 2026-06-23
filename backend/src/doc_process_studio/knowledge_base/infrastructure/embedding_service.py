"""Ollama 文本向量化实现。

实现 EmbeddingService 端口，委托 service/embedding.py 的纯函数。
"""

from collections.abc import Sequence

from ..application.ports import EmbeddingService
from ..service.embedding import embed_texts as _embed_texts


class OllamaEmbeddingService(EmbeddingService):
    """基于 Ollama 的文本向量化服务。"""

    async def embed_texts(self, texts: Sequence[str], model: str | None = None) -> list[list[float]]:
        return await _embed_texts(texts, model=model)
