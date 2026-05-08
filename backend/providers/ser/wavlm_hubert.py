import threading
from typing import Optional

from .base import SERProvider, SERResponse
from ..base import ProviderStatus


class WavlmHubertSERProvider(SERProvider):
    name = "wavlm_hubert"

    def __init__(self, model_path: str = "models/ser/wavlm_hubert_optimized_seed42.pth"):
        self._model_path = model_path
        self._model = None

    async def startup(self):
        def _load():
            try:
                from .joint_ser import SERModel
                self._model = SERModel(self._model_path)
                self._model.load()
            except Exception as e:
                print(f"[SER] Load failed: {e}")

        t = threading.Thread(target=_load, daemon=True)
        t.start()

    async def shutdown(self):
        if self._model:
            self._model.unload()
            self._model = None

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._model is not None and self._model._model is not None,
            error=None if self._model and self._model._model else "SER not loaded",
        )

    async def predict(self, audio_data: bytes, sample_rate: int = 16000) -> SERResponse:
        if not self._model or not self._model._model:
            return SERResponse(emotion="neutral", confidence=0.0)

        try:
            probs = self._model.predict(audio_bytes=audio_data)
            emotions = list(probs.keys())
            values = list(probs.values())
            max_idx = max(range(len(values)), key=lambda i: values[i])
            emotion = emotions[max_idx]
            confidence = values[max_idx]
            return SERResponse(emotion=emotion.capitalize(), confidence=float(confidence))
        except Exception:
            return SERResponse(emotion="neutral", confidence=0.0)
