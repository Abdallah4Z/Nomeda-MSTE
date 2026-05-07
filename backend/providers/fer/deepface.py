from typing import Optional

from .base import FERProvider, FERResponse
from ..base import ProviderStatus


class DeepFaceFERProvider(FERProvider):
    name = "deepface"

    def __init__(self, fast_mode: bool = True):
        self._fast_mode = fast_mode
        self._face_cascade = None

    async def startup(self):
        try:
            import cv2
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
        except ImportError:
            pass

    async def health(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            ready=self._face_cascade is not None,
            error=None if self._face_cascade else "OpenCV not available",
        )

    async def predict(self, frame_data: bytes) -> FERResponse:
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)
            return await self.predict_numpy(frame)
        except Exception:
            return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)

    async def predict_numpy(self, frame) -> FERResponse:
        if not self._face_cascade:
            return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)

        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            faces = self._face_cascade.detectMultiScale(gray, 1.1, 5)

            if len(faces) == 0:
                return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)

            if self._fast_mode:
                return FERResponse(emotion="neutral", confidence=0.5, face_detected=True)

            try:
                from deepface import DeepFace
                result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, silent=True)
                if isinstance(result, list):
                    result = result[0]
                emotion = result.get('dominant_emotion', 'neutral')
                confidence = result.get('emotion', {}).get(emotion, 0.5) / 100.0
                x, y, w, h = faces[0]
                return FERResponse(
                    emotion=emotion,
                    confidence=confidence,
                    face_detected=True,
                    bounding_box=(int(x), int(y), int(w), int(h)),
                )
            except ImportError:
                return FERResponse(emotion="neutral", confidence=0.5, face_detected=True)
        except Exception:
            return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)
