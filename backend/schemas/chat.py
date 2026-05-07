from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str


class FusionData(BaseModel):
    face: Optional[str] = None
    voice: Optional[str] = None
    distress: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    face_emotion: Optional[str] = None
    voice_emotion: Optional[str] = None
    distress: Optional[int] = None
    rag_sources: Optional[list] = None
    tts_audio_url: Optional[str] = None
    tts_audio_b64: Optional[str] = None
