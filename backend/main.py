import os
import sys

# Ensure the project root is on sys.path for existing module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .core.container import Container
from .core.events import event_bus, EventType, Event
from .core.session import SessionManager
from .core.orchestrator import Orchestrator
from .core.state import system_state
from .storage.csv_store import CSVSessionStore
from .api.routes import session_router, chat_router, media_router, admin_router, tts_router
from .api.websocket import router as ws_router
from .utils.logging import setup_logging, get_logger


def create_container(settings: Settings) -> Container:
    container = Container(settings)

    # -- Storage --
    store = CSVSessionStore(sessions_dir=settings.storage.sessions_dir)
    container.store = store

    # -- Providers (lazy init via config) --
    provider_map = {}

    # LLM
    llm_provider_key = settings.llm.provider
    if llm_provider_key == "groq":
        from .providers.llm.groq import GroqLLMProvider
        provider_map["llm"] = GroqLLMProvider(
            api_key=settings.groq_api_key,
            model=settings.llm.model,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
            system_prompt=settings.llm.system_prompt,
        )
    elif llm_provider_key == "openai":
        from .providers.llm.openai import OpenAILikeLLMProvider
        provider_map["llm"] = OpenAILikeLLMProvider(
            api_key=settings.openai_api_key,
            model=settings.llm.model,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
            system_prompt=settings.llm.system_prompt,
        )

    # TTS
    tts_provider_key = settings.tts.provider
    if tts_provider_key == "gemini":
        from .providers.tts.gemini import GeminiTTSProvider
        provider_map["tts"] = GeminiTTSProvider(
            api_key=settings.google_api_key,
            voice=settings.tts.voice,
            model=settings.tts.model,
            tts_dir=settings.storage.tts_dir,
        )
    elif tts_provider_key == "pyttsx3":
        from .providers.tts.pyttsx3 import Pyttsx3TTSProvider
        provider_map["tts"] = Pyttsx3TTSProvider(tts_dir=settings.storage.tts_dir)

    # STT
    stt_provider_key = settings.stt.provider
    if stt_provider_key == "faster_whisper":
        from .providers.stt.faster_whisper import FasterWhisperSTTProvider
        provider_map["stt"] = FasterWhisperSTTProvider(
            model_size=settings.stt.model_size,
            device=settings.stt.device,
            compute_type=settings.stt.compute_type,
        )

    # SER
    ser_provider_key = settings.ser.provider
    if ser_provider_key == "wavlm_hubert":
        from .providers.ser.wavlm_hubert import WavlmHubertSERProvider
        provider_map["ser"] = WavlmHubertSERProvider(model_path=settings.ser.model_path)

    # FER
    fer_provider_key = settings.fer.provider
    if fer_provider_key == "deepface":
        from .providers.fer.deepface import DeepFaceFERProvider
        provider_map["fer"] = DeepFaceFERProvider(
            fast_mode=settings.fer.fast_mode,
            num_threads=settings.fer.num_threads,
            window_size=settings.fer.window_size,
        )

    # RAG
    rag_provider_key = settings.rag.provider
    if rag_provider_key == "chroma":
        from .providers.rag.chroma import ChromaRAGProvider
        provider_map["rag"] = ChromaRAGProvider(
            persist_dir=settings.rag.persist_dir,
            collection_name=settings.rag.collection_name,
            top_k=settings.rag.top_k,
        )

    # Register all providers
    for capability, provider in provider_map.items():
        container.register_provider(capability, provider)

    # -- Session Manager --
    sm = SessionManager(store=store, event_bus=container.event_bus)
    container.session_manager = sm

    # -- Orchestrator --
    orchestrator = Orchestrator(
        llm=container.get_llm(),
        tts=container.get_tts(),
        stt=container.get_stt(),
        ser=container.get_ser(),
        fer=container.get_fer(),
        rag=container.get_rag(),
        session=sm,
        event_bus=container.event_bus,
        tts_distress_threshold=settings.tts.distress_threshold,
        rag_relevance_threshold=1.0,
    )
    container.orchestrator = orchestrator

    return container


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.debug)
    logger = get_logger("nomeda")
    logger.info("Starting Nomeda backend...")

    app.state.container = container
    await container.startup()
    yield
    logger.info("Shutting down Nomeda backend...")
    await container.shutdown()


settings = Settings()
container = create_container(settings)

app = FastAPI(
    title="Nomeda — Multimodal Emotion Monitor",
    version="3.0",
    lifespan=lifespan,
)

# -- CORS --
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Static files --
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def read_root():
    from fastapi.responses import FileResponse
    index = os.path.join(static_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "Nomeda backend running"}


# -- Video feed (legacy) --
@app.get("/video_feed")
async def video_feed():
    from fastapi.responses import StreamingResponse, Response
    import asyncio as _asyncio
    import cv2 as _cv2

    async def generate():
        loop = _asyncio.get_running_loop()
        try:
            cap = await loop.run_in_executor(None, lambda: _cv2.VideoCapture(0))
            if not cap or not cap.isOpened():
                return
        except Exception:
            return
        try:
            while True:
                ret, frame = await loop.run_in_executor(None, cap.read)
                if not ret:
                    break
                _, jpeg = await loop.run_in_executor(
                    None, lambda: _cv2.imencode(".jpg", frame)
                )
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
                )
        finally:
            await loop.run_in_executor(None, cap.release)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# -- Register routes --
app.include_router(session_router)
app.include_router(chat_router)
app.include_router(media_router)
app.include_router(admin_router)
app.include_router(tts_router)
app.include_router(ws_router)
