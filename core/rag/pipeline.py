import time
import hashlib
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from functools import lru_cache

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .config import RAGConfig
from .document_processor import Chunk
from .embeddings import EmbeddingManager
from .vector_store import HybridVectorStore
from .reranker import CrossEncoderReranker
from .retriever import Retriever


@dataclass
class RAGResult:
    response: str
    context_chunks: List[Chunk]
    retrieval_time: float
    generation_time: float
    total_time: float
    n_tokens: int
    speed: float


class RAGPipeline:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self._llm: Optional[AutoModelForCausalLM] = None
        self._tokenizer: Optional[AutoTokenizer] = None

        self.embed_manager = EmbeddingManager(self.config)
        self.vector_store = HybridVectorStore(self.config)
        self.reranker = CrossEncoderReranker(self.config)
        self.retriever = Retriever(self.config, self.vector_store, self.embed_manager, self.reranker)

        self._load_index()

    def _load_index(self):
        self.vector_store = HybridVectorStore.load(self.config)
        if self.vector_store.is_loaded():
            self.retriever = Retriever(self.config, self.vector_store, self.embed_manager, self.reranker)
            print("[+] RAG retriever ready")
        else:
            print("[!] No RAG index found. Run build_rag.py first or place indexed files in data/rag_index/")

    @property
    def llm(self):
        if self._llm is None:
            self._load_llm()
        return self._llm

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self._load_llm()
        return self._tokenizer

    def _load_llm(self):
        repo = self.config.model_repo
        # Check if model weights exist locally before attempting to load
        from pathlib import Path
        repo_path = Path(repo)
        if repo_path.exists():
            has_weights = any(repo_path.glob("*.safetensors")) or any(repo_path.glob("*.bin"))
            if not has_weights:
                print(f"[!] Model config found but weights missing at {repo}. LLM generation disabled.")
                self._tokenizer = AutoTokenizer.from_pretrained(repo, trust_remote_code=True)
                self._llm = None
                return
        print(f"[+] Loading FP16 model: {repo}")
        self._tokenizer = AutoTokenizer.from_pretrained(repo, trust_remote_code=True)
        try:
            self._llm = AutoModelForCausalLM.from_pretrained(
                repo,
                device_map="auto",
                trust_remote_code=True,
                dtype=torch.float16,
                local_files_only=True,
            )
            self._llm.eval()
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    free, total = torch.cuda.mem_get_info(i)
                    print(f"  GPU {i}: {(total - free) / 1e9:.2f}GB used / {total / 1e9:.2f}GB total")
            print("[+] Model loaded")
        except Exception as e:
            print(f"[!] Failed to load LLM: {e}. Running without generation.")
            self._llm = None

    def _clean_response(self, text: str) -> str:
        import re
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        text = re.sub(r'<\|im_end\|>.*$', '', text, flags=re.DOTALL).strip()
        text = re.sub(r'<\|endoftext\|>.*$', '', text, flags=re.DOTALL).strip()
        return text

    def _build_prompt(self, user_message: str, context: str,
                      history: Optional[List[Dict[str, str]]] = None) -> str:
        system = (
            "You are Nomeda, a compassionate mental health AI assistant. "
            "You have access to therapy knowledge from professional resources. "
            "Use the provided context to give evidence-based, empathetic responses. "
            "Keep responses warm, concise (2-4 sentences), and conversational."
        )

        messages = [{"role": "system", "content": system}]

        if context:
            messages.append({
                "role": "system",
                "content": f"Relevant therapy knowledge:\n{context}"
            })

        if history:
            for turn in history[-self.config.max_history_turns * 2:]:
                messages.append(turn)

        messages.append({"role": "user", "content": user_message})

        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    def query(self, user_message: str,
              history: Optional[List[Dict[str, str]]] = None,
              max_tokens: Optional[int] = None,
              temperature: Optional[float] = None,
              stream: bool = False) -> RAGResult:
        t_start = time.time()

        t_retrieval_start = time.time()
        context, chunks = self.retriever.retrieve_context(
            user_message,
            k=self.config.max_context_chunks,
            max_tokens=1500,
        )
        t_retrieval = time.time() - t_retrieval_start

        prompt = self._build_prompt(user_message, context, history)

        max_tok = max_tokens or self.config.max_tokens
        temp = temperature or self.config.temperature

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.llm.device)

        t_gen_start = time.time()
        with torch.no_grad():
            outputs = self.llm.generate(
                **inputs,
                max_new_tokens=max_tok,
                min_new_tokens=self.config.min_new_tokens,
                temperature=temp,
                top_p=self.config.top_p,
                do_sample=True,
                repetition_penalty=self.config.repetition_penalty,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        t_gen = time.time() - t_gen_start

        input_len = inputs["input_ids"].shape[1]
        n_tokens = outputs.shape[1] - input_len
        response = self.tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
        response = self._clean_response(response)

        t_total = time.time() - t_start
        speed = n_tokens / t_gen if t_gen > 0 else 0

        return RAGResult(
            response=response,
            context_chunks=chunks,
            retrieval_time=t_retrieval,
            generation_time=t_gen,
            total_time=t_total,
            n_tokens=n_tokens,
            speed=speed,
        )
