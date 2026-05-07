import asyncio
import base64
import os
import time
from typing import Optional

from .base import TTSProvider, TTSResponse
from ..base import ProviderStatus


class GeminiTTSProvider(TTSProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-tts-preview",
        voice: str = "Kore",
        tts_dir: str = "data/tts",
    ):
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._tts_dir = tts_dir
        self._client = None

    async def startup(self):
        os.makedirs(self._tts_dir, exist_ok=True)
        if not self._api_key:
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        except ImportError:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._client is not None,
            error=None if self._client else "Gemini client not initialized",
        )

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> TTSResponse:
        if not self._client:
            return TTSResponse(audio_data=b"", mime_type="audio/wav")

        try:
            from google.genai import types

            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                ),
            )

            audio_data = b""
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        audio_data = part.inline_data.data
                        break

            if not audio_data:
                return TTSResponse(audio_data=b"", mime_type="audio/wav")

            ts = int(time.time() * 1000)
            wav_path = os.path.join(self._tts_dir, f"tts_{ts}.wav")
            latest_path = os.path.join(self._tts_dir, "latest.wav")
            with open(wav_path, "wb") as f:
                f.write(audio_data)
            temp_link = latest_path + ".tmp"
            os.symlink(os.path.basename(wav_path), temp_link)
            os.replace(temp_link, latest_path)

            b64 = base64.b64encode(audio_data).decode("utf-8")
            return TTSResponse(
                audio_data=audio_data,
                mime_type="audio/wav",
                sample_rate=24000,
                base64=b64,
                url=f"/api/tts/latest",
            )
        except Exception:
            return TTSResponse(audio_data=b"", mime_type="audio/wav")
