from typing import Optional

from .base import STTProvider, STTResponse
from ..base import ProviderStatus


class FasterWhisperSTTProvider(STTProvider):
    name = "faster_whisper"

    def __init__(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    async def startup(self):
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        except ImportError:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._model is not None,
            error=None if self._model else "Whisper model not loaded",
        )

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> STTResponse:
        if not self._model:
            return STTResponse(text="")

        try:
            import io
            import soundfile as sf
            import numpy as np
            from ...utils.audio import decode_audio

            audio_np = None
            sr = sample_rate

            # 1. Try soundfile directly (handles WAV, FLAC, etc.)
            try:
                buf = io.BytesIO(audio_data)
                audio_np, sr = sf.read(buf)
            except Exception:
                pass

            # 2. Try ffmpeg decode (handles WebM/Opus from browser)
            if audio_np is None:
                try:
                    wav = decode_audio(audio_data, target_sr=sample_rate)
                    if wav:
                        buf = io.BytesIO(wav)
                        audio_np, sr = sf.read(buf)
                except Exception:
                    pass

            # 3. Fallback: raw PCM Int16 (headerless WAV) from browser
            if audio_np is None:
                try:
                    raw = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                    audio_np = raw
                    sr = 48000
                except Exception:
                    pass

            if audio_np is None:
                return STTResponse(text="")

            if sr != sample_rate:
                import librosa
                audio_np = librosa.resample(audio_np, orig_sr=sr, target_sr=sample_rate)

            # Skip audio shorter than 0.5s
            if len(audio_np) < sample_rate * 0.5:
                return STTResponse(text="")

            segments, info = self._model.transcribe(
                audio_np.astype(np.float32),
                language=language,
            )

            text = " ".join(seg.text for seg in segments)
            return STTResponse(
                text=text,
                language=info.language if hasattr(info, 'language') else None,
                duration_seconds=info.duration if hasattr(info, 'duration') else None,
            )
        except Exception:
            return STTResponse(text="")
