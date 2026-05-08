import asyncio
import base64
import os
import struct
import time
from typing import Optional

from .base import TTSProvider, TTSResponse
from ..base import ProviderStatus


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
    data_size = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        sample_rate * channels * bits // 8,
        channels * bits // 8,
        bits,
        b"data",
        data_size,
    )
    return header + pcm_data


class GeminiTTSProvider(TTSProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash-preview-tts",
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

            # Gemini returns raw PCM — wrap in WAV container
            audio_data = _pcm_to_wav(audio_data, sample_rate=24000)

            ts = int(time.time() * 1000)
            wav_path = os.path.join(self._tts_dir, f"tts_{ts}.wav")
            with open(wav_path, "wb") as f:
                f.write(audio_data)
            latest_path = os.path.join(self._tts_dir, "latest.wav")
            if os.path.exists(latest_path):
                os.remove(latest_path)
            os.rename(wav_path, latest_path)

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
