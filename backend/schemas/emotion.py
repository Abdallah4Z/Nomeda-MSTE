from pydantic import BaseModel
from typing import Optional


class EmotionPoint(BaseModel):
    time: float
    face: Optional[str] = None
    voice: Optional[str] = None
    distress: int = 0


class EmotionTimeline(BaseModel):
    points: list[EmotionPoint] = []
