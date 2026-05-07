from pydantic_settings import BaseSettings
from typing import Optional


class LLMSettings(BaseSettings):
    provider: str = "nomeda"
    model: str = "nomeda-lab/nomeda-therapist-2B"
    max_tokens: int = 80
    temperature: float = 0.7
    system_prompt: str = ""


class TTSSettings(BaseSettings):
    provider: str = "qwen"
    voice: str = "Ryan"
    model: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    distress_threshold: int = 0
    language: str = "English"


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
    provider: str = "hybrid_faiss"
    persist_dir: str = "data/rag_index"
    collection_name: str = "emotion_knowledge"
    top_k: int = 5


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
