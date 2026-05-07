"""
Build the RAG index from therapy books in ./books/.
Run this once (or re-run when you add new books).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from core.rag.config import RAGConfig
from core.rag.document_processor import DocumentProcessor
from core.rag.embeddings import EmbeddingManager
from core.rag.vector_store import HybridVectorStore


def main():
    print("=" * 55)
    print("  BUILD RAG INDEX")
    print("=" * 55)

    config = RAGConfig()
    processor = DocumentProcessor(config)

    print("\n[1/4] Loading PDFs...")
    docs = processor.load_pdfs()
    if not docs:
        print("[!] No documents found. Exiting.")
        return

    print("\n[2/4] Chunking documents...")
    t0 = time.time()
    chunks = processor.chunk_documents(docs)
    print(f"      {len(chunks)} chunks created in {time.time() - t0:.2f}s")

    print("\n[3/4] Generating embeddings...")
    embed_manager = EmbeddingManager(config)
    texts = [c.text for c in chunks]
    t0 = time.time()
    embeddings = embed_manager.encode(texts)
    print(f"      {embeddings.shape[0]} embeddings (dim={embeddings.shape[1]}) in {time.time() - t0:.2f}s")

    print("\n[4/4] Building and saving hybrid index...")
    t0 = time.time()
    store = HybridVectorStore(config)
    store.build(chunks, embeddings)
    store.save()
    print(f"      Saved in {time.time() - t0:.2f}s")

    print("\n" + "=" * 55)
    print("  DONE — Index ready for querying")
    print("=" * 55)


if __name__ == "__main__":
    main()
