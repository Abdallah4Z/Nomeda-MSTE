import asyncio
import os
from typing import Any, Dict, List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .base import LLMProvider, LLMResponse
from ..base import ProviderStatus

SYSTEM_PROMPT = (
    "You are Nomeda, a warm and compassionate AI therapist. "
    "Respond as a real therapist would in a spoken conversation: "
    "short, warm, natural sentences. No lists, no markdown, no JSON. "
    "Speak like a caring human in 2-3 sentences."
)


class NomedaLLMProvider(LLMProvider):
    name = "nomeda"

    def __init__(
        self,
        model_path: Optional[str] = None,
        max_tokens: int = 80,
        temperature: float = 0.7,
        system_prompt: str = SYSTEM_PROMPT,
    ):
        self._model_path = model_path
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._system_prompt = system_prompt
        self._model: Optional[AutoModelForCausalLM] = None
        self._tokenizer: Optional[AutoTokenizer] = None

    async def startup(self):
        path = self._model_path
        if not path:
            local = os.path.join(
                os.path.dirname(__file__), "..", "..", "..",
                "models", "nomeda-therapist-2B",
            )
            if os.path.exists(local):
                path = os.path.abspath(local)
            else:
                path = "nomeda-lab/nomeda-therapist-2B"

        print(f"[NomedaLLM] Loading model from: {path}")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
            self._model = AutoModelForCausalLM.from_pretrained(
                path,
                device_map="auto",
                trust_remote_code=True,
                dtype=torch.float16,
            )
            self._model.eval()
            print(f"[NomedaLLM] Model loaded ({sum(p.numel() for p in self._model.parameters())/1e6:.0f}M params)")
        except Exception as e:
            print(f"[NomedaLLM] Load error: {e}")

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._model is not None,
            error=None if self._model else "Model not loaded",
        )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        if not self._model or not self._tokenizer:
            return LLMResponse(text="I'm here with you.")

        prompt = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_tokens or self._max_tokens,
                temperature=temperature or self._temperature,
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        input_len = inputs["input_ids"].shape[1]
        text = self._tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
        text = self._clean(text)

        return LLMResponse(text=text)

    async def generate_with_context(
        self,
        messages: List[Dict[str, str]],
        face_emotion: Optional[str] = None,
        voice_emotion: Optional[str] = None,
        distress: Optional[int] = None,
        rag_context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        parts = [{"role": "system", "content": self._system_prompt}]

        if rag_context:
            parts.append({
                "role": "system",
                "content": f"Relevant therapy knowledge:\n{rag_context}",
            })

        multimodal = []
        if face_emotion:
            multimodal.append(f"Face: {face_emotion}")
        if voice_emotion:
            multimodal.append(f"Voice: {voice_emotion}")
        if distress is not None:
            multimodal.append(f"Distress: {distress}/100")

        user_content = messages[-1]["content"] if messages else ""
        if multimodal:
            user_content = f"[{' | '.join(multimodal)}]\n{user_content}"

        parts.append({"role": "user", "content": user_content})
        return await self.generate(parts, max_tokens, temperature)

    def _clean(self, text: str) -> str:
        import re
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        text = re.sub(r'<\|im_end\|>.*$', '', text, flags=re.DOTALL).strip()
        text = re.sub(r'<\|endoftext\|>.*$', '', text, flags=re.DOTALL).strip()
        return text
