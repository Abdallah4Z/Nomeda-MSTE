from typing import List

from .base import EmbeddingProvider
from ..base import ProviderStatus


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    name = "sentence_transformers"

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    async def startup(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        except ImportError:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._model is not None,
            error=None if self._model else "Model not loaded",
        )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not self._model:
            return [[0.0]] * len(texts)
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return [list(emb) for emb in embeddings]

    async def embed_query(self, text: str) -> List[float]:
        if not self._model:
            return [0.0]
        emb = self._model.encode(text, show_progress_bar=False)
        return list(emb)
