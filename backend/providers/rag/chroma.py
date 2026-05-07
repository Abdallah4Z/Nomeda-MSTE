from typing import Any, Dict, List, Optional

from .base import RAGProvider, RAGDocument
from ..base import ProviderStatus


class ChromaRAGProvider(RAGProvider):
    name = "chroma"

    def __init__(
        self,
        persist_dir: str = "data/processed/chroma_db",
        collection_name: str = "emotion_knowledge",
        top_k: int = 3,
    ):
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._top_k = top_k
        self._db = None

    async def startup(self):
        try:
            from langchain_chroma import Chroma
            from langchain_huggingface import HuggingFaceEmbeddings

            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            self._db = Chroma(
                persist_directory=self._persist_dir,
                embedding_function=embeddings,
                collection_name=self._collection_name,
            )
        except ImportError:
            pass
        except Exception:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._db is not None,
            error=None if self._db else "ChromaDB not initialized",
        )

    async def search(self, query: str, top_k: Optional[int] = None) -> List[RAGDocument]:
        if not self._db:
            return []
        try:
            k = top_k or self._top_k
            results = self._db.similarity_search_with_score(query, k=k)
            docs = []
            for doc, score in results:
                docs.append(RAGDocument(
                    text=doc.page_content,
                    score=float(score),
                    metadata=dict(doc.metadata),
                ))
            return docs
        except Exception:
            return []

    async def add_documents(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> None:
        if not self._db:
            return
        try:
            from langchain.schema import Document
            docs = []
            for i, text in enumerate(texts):
                meta = metadatas[i] if metadatas and i < len(metadatas) else {}
                docs.append(Document(page_content=text, metadata=meta))
            self._db.add_documents(docs)
        except Exception:
            pass
