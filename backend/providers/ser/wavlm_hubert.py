from typing import Optional

from .base import SERProvider, SERResponse
from ..base import ProviderStatus


class WavlmHubertSERProvider(SERProvider):
    name = "wavlm_hubert"

    def __init__(self, model_path: str = "models/ser/wavlm_hubert_optimized_seed42.pth"):
        self._model_path = model_path
        self._model = None
        self._label_encoder = None

    async def startup(self):
        try:
            import sys as _sys
            import os as _os
            project_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
            if project_root not in _sys.path:
                _sys.path.insert(0, project_root)
            from modules.voice.ser_model import SERInference
            self._model = SERInference(self._model_path)
        except ImportError:
            pass
        except Exception:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._model is not None,
            error=None if self._model else "SER model not loaded",
        )

    async def predict(self, audio_data: bytes, sample_rate: int = 16000) -> SERResponse:
        if not self._model:
            return SERResponse(emotion="neutral", confidence=0.0)

        try:
            import io
            import soundfile as sf
            import numpy as np
            import librosa

            buf = io.BytesIO(audio_data)
            waveform, sr = sf.read(buf)
            if sr != sample_rate:
                waveform = librosa.resample(waveform, orig_sr=sr, target_sr=sample_rate)

            emotion, confidence = self._model.predict(waveform)
            return SERResponse(emotion=emotion, confidence=float(confidence))
        except Exception:
            return SERResponse(emotion="neutral", confidence=0.0)
