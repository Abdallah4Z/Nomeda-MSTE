import os
import json
import pickle
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from collections import Counter

import numpy as np
import faiss

from .config import RAGConfig
from .document_processor import Chunk


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: List[Counter] = []
        self.idf: Dict[str, float] = {}
        self.doc_lens: List[int] = []
        self.avgdl: float = 0.0
        self.vocab: Dict[str, int] = {}
        self.docs: List[str] = []

    def fit(self, texts: List[str]):
        self.docs = texts
        self.doc_lens = [len(t.split()) for t in texts]
        self.avgdl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 1.0

        df: Counter = Counter()
        for t in texts:
            terms = set(t.lower().split())
            for term in terms:
                df[term] += 1

        n_docs = len(texts)
        self.idf = {term: np.log((n_docs - freq + 0.5) / (freq + 0.5) + 1.0)
                    for term, freq in df.items()}
        self.vocab = {term: idx for idx, term in enumerate(self.idf)}

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        query_terms = query.lower().split()
        scores = np.zeros(len(self.docs))

        for term in set(query_terms):
            if term not in self.idf:
                continue
            idf = self.idf[term]
            for i, doc in enumerate(self.docs):
                tf = doc.lower().split().count(term)
                if tf > 0:
                    denom = tf + self.k1 * (1 - self.b + self.b * self.doc_lens[i] / self.avgdl)
                    scores[i] += idf * (tf * (self.k1 + 1)) / denom

        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]


class HybridVectorStore:
    def __init__(self, config: RAGConfig):
        self.config = config
        self.index: Optional[faiss.Index] = None
        self.chunks: List[Chunk] = []
        self.bm25: Optional[BM25] = None
        self.dimension: int = 384

    def build(self, chunks: List[Chunk], embeddings: np.ndarray):
        self.chunks = chunks
        self.dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        print(f"[+] FAISS index built: {self.index.ntotal} vectors, dim={self.dimension}")

        texts = [c.text for c in chunks]
        self.bm25 = BM25()
        self.bm25.fit(texts)
        print(f"[+] BM25 index built: {len(texts)} documents")

    def search_dense(self, query_emb: np.ndarray, k: int) -> List[Tuple[int, float]]:
        if self.index is None:
            return []
        scores, indices = self.index.search(query_emb, k)
        return [(int(idx), float(score)) for idx, score in zip(indices[0], scores[0])
                if idx != -1 and score > self.config.similarity_threshold]

    def search_sparse(self, query: str, k: int) -> List[Tuple[int, float]]:
        if self.bm25 is None:
            return []
        return self.bm25.search(query, k)

    def fuse_results(self, dense: List[Tuple[int, float]],
                     sparse: List[Tuple[int, float]],
                     k: int) -> List[Tuple[int, float]]:
        rrf_k = self.config.rrf_k
        scores: Dict[int, float] = {}

        for rank, (idx, _) in enumerate(dense):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        for rank, (idx, _) in enumerate(sparse):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return [(idx, score) for idx, score in ranked]

    def save(self, path: Optional[str] = None):
        save_dir = Path(path or self.config.index_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        if self.index:
            faiss.write_index(self.index, str(save_dir / "index.faiss"))

        with open(save_dir / "chunks.pkl", "wb") as f:
            pickle.dump([c.to_dict() for c in self.chunks], f)

        if self.bm25:
            bm25_data = {
                "k1": self.bm25.k1,
                "b": self.bm25.b,
                "idf": self.bm25.idf,
                "doc_lens": self.bm25.doc_lens,
                "avgdl": self.bm25.avgdl,
                "vocab": self.bm25.vocab,
                "docs": self.bm25.docs,
            }
            with open(save_dir / "bm25.json", "w") as f:
                json.dump(bm25_data, f)

        meta = {"dimension": self.dimension, "n_chunks": len(self.chunks)}
        with open(save_dir / "meta.json", "w") as f:
            json.dump(meta, f)

        print(f"[+] Saved index to {save_dir}/")

    @classmethod
    def load(cls, config: RAGConfig, path: Optional[str] = None) -> "HybridVectorStore":
        store = cls(config)
        load_dir = Path(path or config.index_dir)

        index_path = load_dir / "index.faiss"
        chunks_path = load_dir / "chunks.pkl"
        meta_path = load_dir / "meta.json"

        if not index_path.exists():
            print(f"[!] Index not found at {load_dir}/")
            return store

        store.index = faiss.read_index(str(index_path))

        with open(chunks_path, "rb") as f:
            raw_chunks = pickle.load(f)
        store.chunks = [Chunk(**c) for c in raw_chunks]

        bm25_path = load_dir / "bm25.json"
        if bm25_path.exists():
            with open(bm25_path) as f:
                bm25_data = json.load(f)
            store.bm25 = BM25(k1=bm25_data["k1"], b=bm25_data["b"])
            store.bm25.idf = bm25_data["idf"]
            store.bm25.doc_lens = bm25_data["doc_lens"]
            store.bm25.avgdl = bm25_data["avgdl"]
            store.bm25.vocab = bm25_data["vocab"]
            store.bm25.docs = bm25_data["docs"]

        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            store.dimension = meta.get("dimension", 384)

        print(f"[+] Loaded FAISS index ({store.index.ntotal} vectors) and {len(store.chunks)} chunks")
        return store

    def is_loaded(self) -> bool:
        return self.index is not None and len(self.chunks) > 0
