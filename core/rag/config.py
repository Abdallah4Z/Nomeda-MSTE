from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RAGConfig:
    # Paths
    books_dir: str = str(Path(__file__).resolve().parent.parent.parent / "books")
    index_dir: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "rag_index")
    cache_dir: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "cache")

    # Embedding
    embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embed_device: str = "cpu"
    embed_batch_size: int = 64
    embed_cache_size: int = 10000
    embed_normalize: bool = True

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64
    chunk_separators: list = field(default_factory=lambda: ["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""])

    # Retrieval
    top_k_dense: int = 10
    top_k_sparse: int = 10
    top_k_fused: int = 10
    top_k_rerank: int = 5
    similarity_threshold: float = 0.15
    rrf_k: int = 60

    # Reranker
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_device: str = "cpu"

    # Generation
    model_repo: str = "nomeda-lab/nomeda-therapist-2B"
    max_context_chunks: int = 3
    max_tokens: int = 80
    min_new_tokens: int = 10
    temperature: float = 0.7
    top_p: float = 0.9
    repetition_penalty: float = 1.1
    max_history_turns: int = 4

    # Cache
    response_cache_size: int = 500
    response_cache_ttl: int = 3600

    def __post_init__(self):
        local = Path(__file__).resolve().parent.parent.parent / "models" / "nomeda-therapist-2B"
        if local.exists():
            self.model_repo = str(local)
