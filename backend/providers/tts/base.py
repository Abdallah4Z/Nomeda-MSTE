from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..base import BaseProvider, ProviderStatus


@dataclass
class TTSResponse:
    audio_data: bytes
    mime_type: str = "audio/wav"
    sample_rate: int = 24000
    duration_seconds: Optional[float] = None
    url: Optional[str] = None
    base64: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TTSProvider(BaseProvider):
    name: str = "tts"

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> TTSResponse:
        ...
