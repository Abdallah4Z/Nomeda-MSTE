from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..base import BaseProvider, ProviderStatus


@dataclass
class LLMResponse:
    text: str
    distress: Optional[int] = None
    emotion: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    rag_sources: List[Dict[str, Any]] = field(default_factory=list)
    tts_audio_url: Optional[str] = None


class LLMProvider(BaseProvider):
    name: str = "llm"

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        ...

    @abstractmethod
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
        ...
