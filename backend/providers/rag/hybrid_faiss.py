import os
from typing import Any, Dict, List, Optional

from .base import RAGProvider, RAGDocument
from ..base import ProviderStatus
from core.rag.config import RAGConfig
from core.rag.vector_store import HybridVectorStore
from core.rag.embeddings import EmbeddingManager


class HybridFaissRAGProvider(RAGProvider):
    name = "hybrid_faiss"

    def __init__(
        self,
        index_dir: Optional[str] = None,
        top_k: int = 5,
    ):
        self._index_dir = index_dir
        self._top_k = top_k
        self._store: Optional[HybridVectorStore] = None
        self._embeddings: Optional[EmbeddingManager] = None

    async def startup(self):
        config = RAGConfig()
        if self._index_dir:
            config.index_dir = self._index_dir
        os.makedirs(config.index_dir, exist_ok=True)

        self._store = HybridVectorStore.load(config)
        if self._store.is_loaded():
            self._embeddings = EmbeddingManager(config)

    async def health(self) -> ProviderStatus:
        ready = self._store is not None and self._store.is_loaded()
        return ProviderStatus(
            name=self.name,
            ready=ready,
            error=None if ready else "FAISS index not loaded",
            metadata={
                "n_chunks": len(self._store.chunks) if self._store else 0,
            },
        )

    async def search(self, query: str, top_k: Optional[int] = None) -> List[RAGDocument]:
        if not self._store or not self._store.is_loaded():
            return []

        k = top_k or self._top_k
        query_emb = self._embeddings.encode_query(query)
        dense = self._store.search_dense(query_emb, k * 2)
        sparse = self._store.search_sparse(query, k * 2)
        fused = self._store.fuse_results(dense, sparse, k)

        docs = []
        for idx, score in fused:
            if 0 <= idx < len(self._store.chunks):
                chunk = self._store.chunks[idx]
                docs.append(RAGDocument(
                    text=chunk.text,
                    score=float(score),
                    metadata={"source": chunk.source, "page": chunk.page},
                ))
        return docs

    async def add_documents(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> None:
        pass
