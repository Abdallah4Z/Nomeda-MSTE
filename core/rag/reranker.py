from typing import List, Tuple, Optional

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from .config import RAGConfig
from .document_processor import Chunk


class CrossEncoderReranker:
    def __init__(self, config: RAGConfig):
        self.config = config
        self._model: Optional[AutoModelForSequenceClassification] = None
        self._tokenizer: Optional[AutoTokenizer] = None

    @property
    def model(self):
        if self._model is None:
            name = self.config.reranker_model
            device = self.config.reranker_device
            print(f"[+] Loading reranker: {name}")
            self._tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                name, trust_remote_code=True
            ).to(device).eval()
        return self._model

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            _ = self.model
        return self._tokenizer

    def rerank(self, query: str, chunks: List[Tuple[Chunk, float]], top_k: int = 5) -> List[Tuple[Chunk, float]]:
        if not chunks:
            return []

        if len(chunks) <= 3:
            return chunks[:top_k]

        pairs = [(query, c.text) for c, _ in chunks]

        with torch.no_grad():
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self.config.reranker_device)

            logits = self.model(**inputs).logits
            scores = logits.squeeze(-1).cpu().numpy().tolist()

        scored = [(chunks[i][0], scores[i]) for i in range(len(chunks))]
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:top_k]
