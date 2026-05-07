"""
FusionAgent: Multi-modal emotion fusion + RAG-enhanced LLM generation.
Pipeline: FER + SER + STT → RAG retrieval → LLM generation → TTS-ready text.
"""

import os
import json
import time
from typing import Optional, List, Dict
from pathlib import Path

import torch
import numpy as np

from core.rag.config import RAGConfig
from core.rag.pipeline import RAGPipeline

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ── TTS-optimised system prompt ──────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are Nomeda, a warm and compassionate AI therapist. "
    "You are in a live video session with a user. "
    "You see their facial expressions and hear their voice. "
    "Respond as a real therapist would in a spoken conversation: "
    "short, warm, natural sentences. No lists, no markdown, no JSON. "
    "Use the therapy knowledge context when relevant. "
    "Speak like a caring human — 2-3 sentences max."
)

DISTRESS_PROMPT = (
    "Based on the user's facial emotion, voice tone, and what they said, "
    "rate their distress level from 0-100. Reply with ONLY a number."
)


class FusionAgent:
    def __init__(self):
        self.config = RAGConfig()
        self.pipeline: Optional[RAGPipeline] = None
        self.history: List[Dict[str, str]] = []
        self._init_rag()

    def _init_rag(self):
        try:
            self.pipeline = RAGPipeline(self.config)
            if self.pipeline.vector_store.is_loaded():
                print("[FusionAgent] RAG pipeline ready with therapy knowledge")
            else:
                print("[FusionAgent] RAG pipeline loaded (no index — running without RAG)")
        except Exception as e:
            print(f"[FusionAgent] RAG init warning: {e}")
            self.pipeline = None

    def fuse_inputs(
        self,
        face_emotion: str = "neutral",
        voice_emotion: str = "neutral",
        biometric: str = "",
        stt_text: str = "",
    ) -> dict:
        query = stt_text or f"{face_emotion} {voice_emotion}"
        context = ""
        chunks = []

        if self.pipeline and self.pipeline.vector_store.is_loaded():
            try:
                context, chunks = self.pipeline.retriever.retrieve_context(
                    query, k=self.config.max_context_chunks, max_tokens=1200,
                )
            except Exception as e:
                print(f"[FusionAgent] RAG retrieval error: {e}")

        prompt = self._build_tts_prompt(face_emotion, voice_emotion, biometric, stt_text, context)
        response_text = self._generate(prompt)

        if response_text:
            self.history.append({"role": "user", "content": stt_text or query})
            self.history.append({"role": "assistant", "content": response_text})
            if len(self.history) > self.config.max_history_turns * 2:
                self.history = self.history[-(self.config.max_history_turns * 2):]

        distress = self._estimate_distress(face_emotion, voice_emotion, stt_text)

        return {
            "distress": distress,
            "response": response_text or "I'm here with you. How are you feeling?",
        }

    def _build_tts_prompt(
        self,
        face_emotion: str,
        voice_emotion: str,
        biometric: str,
        stt_text: str,
        context: str,
    ) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if context:
            messages.append({
                "role": "system",
                "content": f"Relevant therapy knowledge:\n{context}",
            })

        if self.history:
            for turn in self.history[-(self.config.max_history_turns * 2):]:
                messages.append(turn)

        multimodal = f"[Face: {face_emotion}] [Voice: {voice_emotion}]"
        if biometric:
            multimodal += f" [Bio: {biometric}]"
        user_content = f"{multimodal}\n\nUser says: {stt_text}" if stt_text else multimodal
        messages.append({"role": "user", "content": user_content})

        return self._apply_template(messages)

    def _apply_template(self, messages: List[Dict]) -> str:
        tok = self._get_tokenizer()
        if tok and hasattr(tok, "apply_chat_template"):
            return tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        result = ""
        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == "system":
                result += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                result += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                result += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        result += "<|im_start|>assistant\n"
        return result

    def _get_tokenizer(self):
        if self.pipeline:
            return self.pipeline.tokenizer
        return None

    def _get_llm(self):
        if self.pipeline:
            return self.pipeline.llm
        return None

    def _generate(self, prompt: str) -> Optional[str]:
        llm = self._get_llm()
        tokenizer = self._get_tokenizer()
        if llm is None or tokenizer is None:
            return None

        try:
            inputs = tokenizer(prompt, return_tensors="pt").to(llm.device)
            with torch.no_grad():
                outputs = llm.generate(
                    **inputs,
                    max_new_tokens=self.config.max_tokens,
                    min_new_tokens=self.config.min_new_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    do_sample=True,
                    repetition_penalty=self.config.repetition_penalty,
                    pad_token_id=tokenizer.eos_token_id,
                )
            input_len = inputs["input_ids"].shape[1]
            response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
            return self._clean_response(response)
        except Exception as e:
            print(f"[FusionAgent] Generation error: {e}")
            return None

    def ensure_llm_loaded(self):
        import torch
        if not self.pipeline or self.pipeline._llm is None:
            return
        dev = next(self.pipeline._llm.parameters()).device
        if str(dev) == "cpu":
            print("[FusionAgent] Moving LLM to GPU...")
            self.pipeline._llm = self.pipeline._llm.to("cuda")
            torch.cuda.empty_cache()

    def offload_llm(self):
        import torch
        if self.pipeline and self.pipeline._llm is not None:
            self.pipeline._llm = self.pipeline._llm.to("cpu")
            torch.cuda.empty_cache()
            print("[FusionAgent] LLM offloaded to CPU")

    def _clean_response(self, text: str) -> str:
        import re
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        text = re.sub(r'<\|im_end\|>.*$', '', text, flags=re.DOTALL).strip()
        text = re.sub(r'<\|endoftext\|>.*$', '', text, flags=re.DOTALL).strip()
        return text

    def _estimate_distress(self, face_emotion: str, voice_emotion: str, stt_text: str) -> int:
        high_words = ["anxious", "scared", "terrified", "hopeless", "suicidal",
                      "panic", "depressed", "angry", "furious", "devastated", "crisis"]
        mid_words = ["sad", "worried", "nervous", "stressed", "upset", "frustrated",
                     "lonely", "tired", "overwhelmed", "confused"]

        distress = 30
        face_lower = face_emotion.lower()
        voice_lower = voice_emotion.lower()
        text_lower = stt_text.lower()

        if any(w in face_lower for w in ["angry", "fear", "sad", "disgust"]):
            distress += 20
        if any(w in voice_lower for w in ["angry", "fear", "sad", "high arousal"]):
            distress += 15
        if any(w in text_lower for w in high_words):
            distress += 25
        elif any(w in text_lower for w in mid_words):
            distress += 10
        if any(w in face_lower for w in ["happy", "calm", "neutral"]):
            distress -= 10

        return max(0, min(100, distress))

    def fuse_inputs_fast(
        self,
        face_emotion: str = "neutral",
        voice_emotion: str = "neutral",
        biometric: str = "",
        stt_text: str = "",
        max_tokens: int = 128,
    ) -> dict:
        old_max = self.config.max_tokens
        self.config.max_tokens = max_tokens
        result = self.fuse_inputs(face_emotion, voice_emotion, biometric, stt_text)
        self.config.max_tokens = old_max
        return result


if __name__ == "__main__":
    agent = FusionAgent()
    result = agent.fuse_inputs(
        face_emotion="Happy",
        voice_emotion="Neutral",
        biometric="HR: 72",
        stt_text="I feel much better today, thanks for asking.",
    )
    print(f"Result: {json.dumps(result, indent=2)}")
