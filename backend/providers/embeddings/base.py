from abc import abstractmethod
from typing import List

from ..base import BaseProvider


class EmbeddingProvider(BaseProvider):
    name: str = "embeddings"

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        ...
