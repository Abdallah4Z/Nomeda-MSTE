from typing import List, Tuple, Optional

from .config import RAGConfig
from .document_processor import Chunk
from .embeddings import EmbeddingManager
from .vector_store import HybridVectorStore
from .reranker import CrossEncoderReranker


class Retriever:
    def __init__(self, config: RAGConfig, vector_store: HybridVectorStore,
                 embed_manager: EmbeddingManager,
                 reranker: Optional[CrossEncoderReranker] = None):
        self.config = config
        self.vector_store = vector_store
        self.embed_manager = embed_manager
        self.reranker = reranker

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Tuple[Chunk, float]]:
        if not self.vector_store.is_loaded():
            return []

        top_k = k or self.config.top_k_rerank

        query_emb = self.embed_manager.encode_query(query)

        dense_results = self.vector_store.search_dense(query_emb, self.config.top_k_dense)
        sparse_results = self.vector_store.search_sparse(query, self.config.top_k_sparse)

        fused = self.vector_store.fuse_results(dense_results, sparse_results, self.config.top_k_fused)

        chunks_with_scores = []
        for idx, score in fused:
            if 0 <= idx < len(self.vector_store.chunks):
                chunks_with_scores.append((self.vector_store.chunks[idx], score))

        if self.reranker and len(chunks_with_scores) > 3:
            chunks_with_scores = self.reranker.rerank(query, chunks_with_scores, top_k)

        return chunks_with_scores[:top_k]

    def retrieve_context(self, query: str, k: Optional[int] = None,
                         max_tokens: int = 1500) -> Tuple[str, List[Chunk]]:
        results = self.retrieve(query, k)
        context_parts = []
        used_chunks = []
        token_budget = max_tokens

        for chunk, score in results:
            est_tokens = chunk.n_tokens or (len(chunk.text) // 4)
            if est_tokens <= token_budget:
                context_parts.append(chunk.text)
                used_chunks.append(chunk)
                token_budget -= est_tokens
            else:
                break

        context = "\n\n".join(context_parts) if context_parts else ""
        return context, used_chunks
