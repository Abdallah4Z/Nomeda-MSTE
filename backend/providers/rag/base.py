from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..base import BaseProvider, ProviderStatus


@dataclass
class RAGDocument:
    text: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGProvider(BaseProvider):
    name: str = "rag"

    @abstractmethod
    async def search(self, query: str, top_k: int = 3) -> List[RAGDocument]:
        ...

    @abstractmethod
    async def add_documents(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> None:
        ...

    async def format_context(self, query: str, top_k: Optional[int] = None) -> str:
        docs = await self.search(query, top_k or 3)
        if not docs:
            return ""
        return "\n\n".join(f"[Source: {d.metadata.get('source', 'knowledge')}]\n{d.text}" for d in docs)
