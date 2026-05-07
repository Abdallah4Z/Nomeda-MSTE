from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..base import BaseProvider, ProviderStatus


@dataclass
class SERResponse:
    emotion: str
    confidence: float
    distress: Optional[float] = None


class SERProvider(BaseProvider):
    name: str = "ser"

    @abstractmethod
    async def predict(self, audio_data: bytes, sample_rate: int = 16000) -> SERResponse:
        ...
