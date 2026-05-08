import base64
from typing import Any, Dict, List, Optional

from ..providers.llm import LLMProvider, LLMResponse
from ..providers.tts import TTSProvider
from ..providers.stt import STTProvider
from ..providers.ser import SERProvider, SERResponse
from ..providers.fer import FERProvider, FERResponse
from ..providers.rag import RAGProvider
from .session import SessionManager
from .events import EventBus, Event, EventType


class Orchestrator:
    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        tts: Optional[TTSProvider] = None,
        stt: Optional[STTProvider] = None,
        ser: Optional[SERProvider] = None,
        fer: Optional[FERProvider] = None,
        rag: Optional[RAGProvider] = None,
        session: Optional[SessionManager] = None,
        event_bus: Optional[EventBus] = None,
        tts_distress_threshold: int = 0,
        rag_relevance_threshold: float = 1.0,
        runtime_config: Optional["RuntimeConfig"] = None,
    ):
        self._llm = llm
        self._tts = tts
        self._stt = stt
        self._ser = ser
        self._fer = fer
        self._rag = rag
        self._session = session
        self._event_bus = event_bus
        self._tts_distress_threshold = tts_distress_threshold
        self._rag_relevance_threshold = rag_relevance_threshold
        self._runtime_config = runtime_config

    async def process_chat_message(
        self,
        text: str,
        conversation_history: Optional[list[dict]] = None,
        face_emotion: Optional[str] = None,
        voice_emotion: Optional[str] = None,
        distress: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not self._llm:
            return {"response": "I'm here with you.", "face_emotion": face_emotion, "voice_emotion": voice_emotion}

        rag_context = ""
        rag_sources = []
        if self._rag:
            try:
                results = await self._rag.search(text, top_k=3)
                if results:
                    threshold = self._rag_relevance_threshold
                    if self._runtime_config:
                        threshold = self._runtime_config.rag_relevance_threshold
                    filtered = [r for r in results if r.score <= threshold]
                    rag_sources = [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in filtered]
                    if filtered:
                        rag_context = await self._rag.format_context(text)
            except Exception:
                pass

        messages = list(conversation_history) if conversation_history else []
        messages.append({"role": "user", "content": text})

        response = await self._llm.generate_with_context(
            messages=messages,
            face_emotion=face_emotion,
            voice_emotion=voice_emotion,
            distress=distress,
            rag_context=rag_context,
        )

        if self._session:
            self._session.add_message("ai", response.text, fusion={
                "face": face_emotion,
                "voice": voice_emotion,
                "distress": distress,
            })

        tts_audio_url = response.tts_audio_url
        tts_audio_b64 = None

        distress_val = response.distress or distress or 0
        tts_enabled = True
        if self._runtime_config:
            tts_enabled = self._runtime_config.get("tts.enabled", True) and self._runtime_config.get("tts.auto_play", True)
        if self._tts and distress_val >= self._tts_distress_threshold and tts_enabled:
            try:
                tts_result = await self._tts.synthesize(response.text)
                if tts_result.base64:
                    tts_audio_b64 = tts_result.base64
                if tts_result.url:
                    tts_audio_url = tts_result.url
            except Exception:
                pass

        return {
            "response": response.text,
            "face_emotion": face_emotion,
            "voice_emotion": voice_emotion,
            "distress": distress_val,
            "rag_sources": rag_sources,
            "tts_audio_url": tts_audio_url,
            "tts_audio_b64": tts_audio_b64,
        }

    async def process_browser_frame(self, frame_data: bytes) -> Optional[FERResponse]:
        if not self._fer:
            return None
        try:
            result = await self._fer.predict(frame_data)
            return result
        except Exception:
            return None

    async def process_voice_note(
        self,
        audio_data: bytes,
    ) -> Dict[str, Any]:
        transcript = ""
        emotion = None

        if self._stt:
            try:
                stt_result = await self._stt.transcribe(audio_data)
                transcript = stt_result.text
            except Exception:
                pass

        if self._ser:
            try:
                ser_result = await self._ser.predict(audio_data)
                emotion = ser_result.emotion
            except Exception:
                pass

        return {
            "transcript": transcript,
            "emotion": emotion,
        }
