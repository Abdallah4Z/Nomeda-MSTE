import json
import re
from typing import Any, Dict, List, Optional

from .base import LLMProvider, LLMResponse
from ..base import ProviderStatus


class GroqLLMProvider(LLMProvider):
    name = "groq"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: str = "You are a compassionate AI therapist.",
    ):
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._system_prompt = system_prompt
        self._client = None

    async def startup(self):
        if not self._api_key:
            return
        try:
            from langchain_groq import ChatGroq
            client = ChatGroq(
                api_key=self._api_key,
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            import asyncio
            try:
                await asyncio.wait_for(
                    client.ainvoke([{"role": "user", "content": "ping"}]), timeout=5
                )
            except Exception:
                pass
            self._client = client
        except ImportError:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._client is not None,
            error=None if self._client else "Groq client not initialized",
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
            from langchain_core.messages import HumanMessage, SystemMessage

            full_messages = [SystemMessage(content=self._system_prompt)]
            for msg in messages:
                role = msg.get("role", "user")
                if role == "user":
                    full_messages.append(HumanMessage(content=msg["content"]))
                elif role == "assistant":
                    from langchain_core.messages import AIMessage
                    full_messages.append(AIMessage(content=msg["content"]))
                elif role == "system":
                    full_messages.append(SystemMessage(content=msg["content"]))

            result = await self._client.ainvoke(
                full_messages,
                max_tokens=max_tokens or self._max_tokens,
                temperature=temperature or self._temperature,
            )
            text = result.content if hasattr(result, 'content') else str(result)
            return self._parse_response(text)
        except Exception as e:
            return LLMResponse(text=f"I'm here with you.", distress=0)

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
                "role": "system",
                "content": f"[REFERENCE CONTEXT — IGNORE IF NOT RELEVANT]\n{context_str}"
            })

        return await self.generate(enriched_messages, max_tokens, temperature)

    def _parse_response(self, text: str) -> LLMResponse:
        distress = None
        rag = []
        clean_text = text

        # Try to extract JSON from the response (the model is instructed to output JSON)
        try:
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                distress = data.get("distress")
                if "response" in data:
                    clean_text = data["response"]
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: keyword-based distress detection if JSON parsing didn't yield a distress score
        if distress is None:
            distress_patterns = {
                80: re.compile(r'\b(crisis|severe|extremely|desperate|can\'t go on)\b', re.I),
                60: re.compile(r'\b(very|really|struggling|hard|difficult|overwhelmed)\b', re.I),
                40: re.compile(r'\b(somewhat|moderate|bit|slightly|manage)\b', re.I),
                20: re.compile(r'\b(mild|little|okay|fine|alright)\b', re.I),
            }
            for level, pattern in distress_patterns.items():
                if pattern.search(text):
                    distress = level
                    break

        return LLMResponse(text=clean_text.strip(), distress=distress or 0, rag_sources=rag)
