import base64
import os
import tempfile
from typing import Optional

from .base import TTSProvider, TTSResponse
from ..base import ProviderStatus


class Pyttsx3TTSProvider(TTSProvider):
    name = "pyttsx3"

    def __init__(self, tts_dir: str = "data/tts"):
        self._tts_dir = tts_dir
        self._engine = None

    async def startup(self):
        os.makedirs(self._tts_dir, exist_ok=True)
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
        except ImportError:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._engine is not None,
            error=None if self._engine else "pyttsx3 not available",
        )

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> TTSResponse:
        if not self._engine:
            return TTSResponse(audio_data=b"", mime_type="audio/wav")

        try:
            import wave
            import io

            wav_path = os.path.join(self._tts_dir, "latest.wav")
            self._engine.save_to_file(text, wav_path)
            self._engine.runAndWait()

            with open(wav_path, "rb") as f:
                audio_data = f.read()

            b64 = base64.b64encode(audio_data).decode("utf-8")
            return TTSResponse(
                audio_data=audio_data,
                mime_type="audio/wav",
                sample_rate=22050,
                base64=b64,
                url=f"/api/tts/latest",
            )
        except Exception as e:
            return TTSResponse(audio_data=b"", mime_type="audio/wav")
