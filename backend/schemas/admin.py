from pydantic import BaseModel
from typing import Optional


class SystemStatus(BaseModel):
    running: bool = False
    total_sessions: int = 0
    avg_distress: Optional[float] = None
    models_ready: int = 0
    models_total: int = 0
    recent_sessions: list = []


class ConfigUpdate(BaseModel):
    llm_mode: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    tts_backend: Optional[str] = None
    tts_threshold: Optional[int] = None
    camera_source: Optional[str] = None
    camera_id: Optional[int] = None
    groq_key: Optional[str] = None


class ModelStatus(BaseModel):
    name: str
    description: str = ""
    status: str = "unknown"  # ready, loading, error
