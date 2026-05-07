from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..base import BaseProvider, ProviderStatus


@dataclass
class STTResponse:
    text: str
    language: Optional[str] = None
    segments: Optional[list] = None
    duration_seconds: Optional[float] = None


class STTProvider(BaseProvider):
    name: str = "stt"

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> STTResponse:
        ...
