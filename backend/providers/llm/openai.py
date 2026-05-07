from typing import Any, Dict, List, Optional

from .base import LLMProvider, LLMResponse
from ..base import ProviderStatus


class OpenAILikeLLMProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: str = "You are a compassionate AI therapist.",
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._system_prompt = system_prompt
        self._client = None

    async def startup(self):
        if not self._api_key:
            return
        try:
            from openai import AsyncOpenAI
            kwargs = {"api_key": self._api_key, "max_retries": 2}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        except ImportError:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._client is not None,
            error=None if self._client else "OpenAI client not initialized",
        )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        if not self._client:
            return LLMResponse(text="I'm here with you.", distress=0)

        try:
            full_messages = [{"role": "system", "content": self._system_prompt}]
            for msg in messages:
                full_messages.append({"role": msg.get("role", "user"), "content": msg["content"]})

            result = await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                max_tokens=max_tokens or self._max_tokens,
                temperature=temperature or self._temperature,
            )
            text = result.choices[0].message.content or ""
            return LLMResponse(text=text)
        except Exception as e:
            return LLMResponse(text="I'm here with you.", distress=0)

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
        context_parts = []
        if face_emotion:
            context_parts.append(f"Facial emotion: {face_emotion}")
        if voice_emotion:
            context_parts.append(f"Voice emotion: {voice_emotion}")
        if distress is not None:
            context_parts.append(f"Distress level: {distress}/100")
        if rag_context:
            context_parts.append(f"Relevant context:\n{rag_context}")

        context_str = "\n".join(context_parts)
        enriched_messages = list(messages)
        if context_str:
            enriched_messages.insert(0, {
                "role": "user",
                "content": f"[Context from monitoring system]\n{context_str}"
            })

        return await self.generate(enriched_messages, max_tokens, temperature)
