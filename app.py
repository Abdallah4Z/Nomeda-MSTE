"""
Nomeda Therapist: RAG-powered mental health AI
Production-grade CLI app using FP16 model + therapy book knowledge.
"""

import os
import time
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.rag.config import RAGConfig
from core.rag.pipeline import RAGPipeline


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    clear_screen()
    print(r"""
  ╔══════════════════════════════════════════════════╗
  ║              NOMEDA THERAPIST                    ║
  ║     RAG-Powered Mental Health AI Assistant       ║
  ╚══════════════════════════════════════════════════╝
    """)


def print_help():
    print("  Commands:")
    print("    /help       - Show this help")
    print("    /clear      - Clear screen")
    print("    /history    - Show conversation history")
    print("    /stats      - Show session stats")
    print("    /quit       - Exit")
    print()


class ChatSession:
    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline
        self.history: List[Dict[str, str]] = []
        self.total_tokens = 0
        self.total_time = 0.0
        self.n_queries = 0

    def add_turn(self, user: str, assistant: str):
        self.history.append({"role": "user", "content": user})
        self.history.append({"role": "assistant", "content": assistant})

    def print_stats(self):
        print(f"\n  ── Session Stats ──")
        print(f"  Queries:     {self.n_queries}")
        print(f"  Total tokens: {self.total_tokens}")
        print(f"  Total time:   {self.total_time:.1f}s")
        avg = self.total_time / max(self.n_queries, 1)
        print(f"  Avg latency:  {avg:.2f}s")
        print()

    def run(self):
        print_banner()
        print("  Type your message to start a conversation.")
        print_help()

        while True:
            try:
                user_input = input("\n  You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n  Goodbye. Take care of yourself.")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/quit":
                    print("\n  Goodbye. Take care of yourself.\n")
                    break
                elif cmd == "/help":
                    print_help()
                    continue
                elif cmd == "/clear":
                    print_banner()
                    continue
                elif cmd == "/history":
                    self._show_history()
                    continue
                elif cmd == "/stats":
                    self.print_stats()
                    continue
                else:
                    print(f"  Unknown command: {user_input}")
                    continue

            print("  ", end="", flush=True)
            result = self.pipeline.query(
                user_message=user_input,
                history=self.history,
            )

            self.total_tokens += result.n_tokens
            self.total_time += result.total_time
            self.n_queries += 1

            print(f"\r  \r", end="")
            print(f"\n  ✦ Nomeda: {result.response}\n")

            if result.context_chunks:
                print(f"  ── Retrieved from: {', '.join(set(c.source for c in result.context_chunks))} "
                      f"({result.retrieval_time:.2f}s retrieval)")

            print(f"  ⚡ {result.speed:.1f} tok/s | {result.n_tokens} tokens | "
                  f"{result.total_time:.2f}s total\n")

            self.add_turn(user_input, result.response)

    def _show_history(self):
        if not self.history:
            print("  No conversation history.\n")
            return
        print(f"\n  ── Conversation History ({len(self.history)//2} turns) ──")
        for msg in self.history[-12:]:
            role = "You" if msg["role"] == "user" else "Nomeda"
            print(f"  [{role}] {msg['content'][:200]}")
        print()


def interactive_mode(pipeline: RAGPipeline):
    session = ChatSession(pipeline)
    session.run()


def single_query_mode(pipeline: RAGPipeline, query: str):
    print(f"\n  You: {query}")
    result = pipeline.query(query)
    print(f"\n  ✦ Nomeda: {result.response}")
    print(f"\n  ⚡ {result.speed:.1f} tok/s | {result.n_tokens} tokens | "
          f"{result.total_time:.2f}s total")
    if result.context_chunks:
        print(f"  Sources: {', '.join(set(c.source for c in result.context_chunks))}")


def main():
    parser = argparse.ArgumentParser(description="Nomeda Therapist — RAG-powered mental health AI")
    parser.add_argument("query", nargs="?", help="Single query (omit for interactive mode)")
    parser.add_argument("--model", default=RAGConfig().model_repo,
                        help="HuggingFace model repo (default: nomeda-lab/nomeda-therapist-2B)")
    parser.add_argument("--index-dir", default=RAGConfig().index_dir,
                        help="Path to RAG index directory")
    parser.add_argument("--no-rag", action="store_true", help="Disable RAG")
    args = parser.parse_args()

    config = RAGConfig()
    if args.index_dir:
        config.index_dir = args.index_dir
    if args.model:
        config.model_repo = args.model

    print("[+] Initializing RAG pipeline...")
    pipeline = RAGPipeline(config)

    if args.no_rag:
        pipeline.retriever = None

    if args.query:
        single_query_mode(pipeline, args.query)
    else:
        interactive_mode(pipeline)


if __name__ == "__main__":
    main()
