import asyncio
import base64
import os
import time
from typing import Optional

from .base import TTSProvider, TTSResponse
from ..base import ProviderStatus


class QwenTTSProvider(TTSProvider):
    name = "qwen"

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        device: str = "cuda:0",
        speaker: str = "Ryan",
        language: str = "English",
        tts_dir: str = "data/tts",
    ):
        self._model_name = model_name
        self._device = device
        self._speaker = speaker
        self._language = language
        self._tts_dir = tts_dir
        self._model = None

    async def startup(self):
        os.makedirs(self._tts_dir, exist_ok=True)
        try:
            from qwen_tts import Qwen3TTSModel
            import torch
            self._model = Qwen3TTSModel.from_pretrained(
                self._model_name,
                device_map=self._device,
                dtype=torch.bfloat16,
                attn_implementation="flash_attention_2",
            )
        except Exception as e:
            print(f"[QwenTTS] Load error: {e}")

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._model is not None,
            error=None if self._model else "QwenTTS model not loaded",
        )

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> TTSResponse:
        if not self._model:
            return TTSResponse(audio_data=b"", mime_type="audio/wav")

        speaker = voice or self._speaker
        try:
            wavs, sr = self._model.generate_custom_voice(
                text=text,
                language=self._language,
                speaker=speaker,
            )

            import numpy as np
            arr = (wavs[0] * 32767).astype(np.int16)
            audio_data = arr.tobytes()

            ts = int(time.time() * 1000)
            wav_path = os.path.join(self._tts_dir, f"tts_{ts}.wav")
            latest_path = os.path.join(self._tts_dir, "latest.wav")

            import wave
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(audio_data)

            temp_link = latest_path + ".tmp"
            os.symlink(os.path.basename(wav_path), temp_link)
            os.replace(temp_link, latest_path)

            b64 = base64.b64encode(audio_data).decode("utf-8")
            duration = len(wavs[0]) / sr if len(wavs[0]) > 0 else 0

            return TTSResponse(
                audio_data=audio_data,
                mime_type="audio/wav",
                sample_rate=sr,
                duration_seconds=duration,
                base64=b64,
                url=f"/api/tts/latest",
            )
        except Exception as e:
            print(f"[QwenTTS] Synthesis error: {e}")
            return TTSResponse(audio_data=b"", mime_type="audio/wav")
