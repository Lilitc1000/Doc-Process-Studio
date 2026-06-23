import logging
from collections.abc import Sequence

import httpx

from ...core.config import settings

logger = logging.getLogger(__name__)


async def embed_texts(texts: Sequence[str], model: str | None = None) -> list[list[float]]:
    if not texts:
        return []

    model_name = model or settings.kb_embedding_model
    base_url = (settings.ollama_base_url or "http://localhost:11434").rstrip("/")
    url = f"{base_url}/api/embed"

    batch_size = settings.kb_embedding_batch_size
    all_embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        for start in range(0, len(texts), batch_size):
            batch = list(texts[start : start + batch_size])
            try:
                response = await client.post(url, json={"model": model_name, "input": batch})
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings", [])
                all_embeddings.extend(embeddings)
            except Exception:
                logger.warning("Embedding batch failed (start=%d)", start, exc_info=True)
                all_embeddings.extend([[0.0] * 768 for _ in batch])

    return all_embeddings
