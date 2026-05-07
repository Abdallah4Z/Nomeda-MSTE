#!/usr/bin/env python3
"""
Standalone RAG test — loads the FP16 model + therapy book index,
then lets you chat. No camera, no mic, no TTS needed.

Usage:
    python test_rag.py
    python test_rag.py "I feel really anxious about my job interview tomorrow"
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.rag.config import RAGConfig
from core.rag.pipeline import RAGPipeline


def single_query(pipeline: RAGPipeline, query: str):
    print(f"\n  You: {query}")
    t0 = time.time()
    result = pipeline.query(query)
    elapsed = time.time() - t0

    print(f"\n  Nomeda: {result.response}")
    print(f"\n  ⚡ {result.speed:.1f} tok/s | {result.n_tokens} tokens | {elapsed:.2f}s")

    if result.context_chunks:
        sources = set(c.source for c in result.context_chunks)
        print(f"  📚 Retrieved from: {', '.join(sources)}")
        print(f"  🔍 Retrieval: {result.retrieval_time:.2f}s | Gen: {result.generation_time:.2f}s")
    print()


def interactive(pipeline: RAGPipeline):
    history = []
    print("\n  Type your message. Commands: /quit, /clear, /stats\n")

    while True:
        try:
            user = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye.")
            break

        if not user:
            continue
        if user.lower() in ("/quit", "/exit", "bye"):
            print("  Nomeda: Take care of yourself.\n")
            break
        if user.lower() == "/clear":
            print("\n" * 2)
            continue
        if user.lower() == "/stats":
            print(f"  History turns: {len(history)}")
            continue

        t0 = time.time()
        result = pipeline.query(user, history=history)
        elapsed = time.time() - t0

        print(f"\n  Nomeda: {result.response}")

        if result.context_chunks:
            sources = set(c.source for c in result.context_chunks)
            print(f"  📚 {', '.join(sources)} | {elapsed:.2f}s")
        else:
            print(f"  ⏱ {elapsed:.2f}s")

        print()

        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": result.response})


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else None

    print("[+] Initialising RAG pipeline...")
    config = RAGConfig()
    pipeline = RAGPipeline(config)

    if not pipeline.vector_store.is_loaded():
        print("[!] No RAG index found. Run first: python scripts/build_rag.py")

    if query:
        single_query(pipeline, query)
    else:
        interactive(pipeline)


if __name__ == "__main__":
    main()
