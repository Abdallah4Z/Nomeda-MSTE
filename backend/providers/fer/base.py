from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..base import BaseProvider, ProviderStatus


@dataclass
class FERResponse:
    emotion: str
    confidence: float
    face_detected: bool = False
    bounding_box: Optional[tuple] = None


class FERProvider(BaseProvider):
    name: str = "fer"

    @abstractmethod
    async def predict(self, frame_data: bytes) -> FERResponse:
        ...

    @abstractmethod
    async def predict_numpy(self, frame) -> FERResponse:
        ...
