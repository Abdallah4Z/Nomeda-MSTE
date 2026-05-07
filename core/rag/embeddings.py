import os
import pickle
import hashlib
from pathlib import Path
from typing import List, Optional, Dict
from functools import lru_cache

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from .config import RAGConfig


class EmbeddingManager:
    def __init__(self, config: RAGConfig):
        self.config = config
        self._model: Optional[SentenceTransformer] = None
        self._cache: Dict[str, np.ndarray] = {}
        self._cache_path = Path(config.cache_dir) / "embedding_cache.pkl"
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_disk_cache()

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            print(f"[+] Loading embedding model: {self.config.embed_model_name}")
            self._model = SentenceTransformer(
                self.config.embed_model_name,
                device=self.config.embed_device,
            )
        return self._model

    def encode(self, texts: List[str]) -> np.ndarray:
        uncached = []
        indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            key = self._hash(text)
            if key in self._cache:
                results[i] = self._cache[key]
            else:
                uncached.append(text)
                indices.append(i)

        if uncached:
            if len(uncached) <= self.config.embed_batch_size:
                embs = self.model.encode(uncached, convert_to_numpy=True, show_progress_bar=False)
            else:
                embs = self.model.encode(
                    uncached,
                    batch_size=self.config.embed_batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=True,
                )
            embs = embs.astype(np.float32)

            for idx, emb, txt in zip(indices, embs, uncached):
                key = self._hash(txt)
                self._cache[key] = emb
                results[idx] = emb

            self._trim_cache()
            self._save_disk_cache()

        final = np.array([r for r in results if r is not None], dtype=np.float32)
        if self.config.embed_normalize:
            faiss.normalize_L2(final)
        return final

    def encode_query(self, query: str) -> np.ndarray:
        emb = self.model.encode([query], convert_to_numpy=True).astype(np.float32)
        if self.config.embed_normalize:
            faiss.normalize_L2(emb)
        return emb

    def _hash(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _trim_cache(self):
        max_size = self.config.embed_cache_size
        if len(self._cache) > max_size:
            keys = list(self._cache.keys())
            for k in keys[:len(keys) - max_size]:
                del self._cache[k]

    def _load_disk_cache(self):
        if self._cache_path.exists():
            try:
                with open(self._cache_path, "rb") as f:
                    self._cache = pickle.load(f)
                print(f"[+] Loaded {len(self._cache)} cached embeddings from disk")
            except Exception:
                self._cache = {}

    def _save_disk_cache(self):
        try:
            with open(self._cache_path, "wb") as f:
                pickle.dump(self._cache, f)
        except Exception:
            pass
