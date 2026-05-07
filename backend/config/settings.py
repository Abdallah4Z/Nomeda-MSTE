from pydantic_settings import BaseSettings
from typing import Optional


class LLMSettings(BaseSettings):
    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"
    max_tokens: int = 512
    temperature: float = 0.7
    system_prompt: str = "You are a compassionate AI therapist."


class TTSSettings(BaseSettings):
    provider: str = "gemini"
    voice: str = "Kore"
    model: str = "gemini-2.0-flash-tts-preview"
    distress_threshold: int = 0


class STTSettings(BaseSettings):
    provider: str = "faster_whisper"
    model_size: str = "tiny"
    device: str = "cpu"
    compute_type: str = "int8"


class FERSettings(BaseSettings):
    provider: str = "deepface"
    fast_mode: bool = True
    microservice_url: str = "http://127.0.0.1:8001/analyze"


class SERSettings(BaseSettings):
    provider: str = "wavlm_hubert"
    model_path: str = "models/ser/wavlm_hubert_optimized_seed42.pth"


class RAGSettings(BaseSettings):
    provider: str = "chroma"
    persist_dir: str = "data/processed/chroma_db"
    collection_name: str = "emotion_knowledge"
    top_k: int = 3


class StorageSettings(BaseSettings):
    provider: str = "csv"
    sessions_dir: str = "data/sessions"
    tts_dir: str = "data/tts"


class Settings(BaseSettings):
    class Config:
        env_prefix: str = "NOMEDA_"
        env_file: str = ".env"
        env_nested_delimiter: str = "__"

    llm: LLMSettings = LLMSettings()
    tts: TTSSettings = TTSSettings()
    stt: STTSettings = STTSettings()
    fer: FERSettings = FERSettings()
    ser: SERSettings = SERSettings()
    rag: RAGSettings = RAGSettings()
    storage: StorageSettings = StorageSettings()

    groq_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    face_analysis_url: str = "http://127.0.0.1:8001"
    camera_source: str = "browser"
    camera_id: int = 0
    debug: bool = False


settings = Settings()
