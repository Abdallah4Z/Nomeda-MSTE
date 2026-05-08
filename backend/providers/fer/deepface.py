from typing import Optional

from .base import FERProvider, FERResponse
from ..base import ProviderStatus

EMOTION_MAP = {
    "angry": "angry",
    "fear": "fear",
    "disgust": "disgust",
    "sad": "sad",
    "neutral": "neutral",
    "happy": "happy",
    "surprise": "surprised",
}


class DeepFaceFERProvider(FERProvider):
    name = "deepface"

    def __init__(self, fast_mode: bool = True, num_threads: int = 2, window_size: int = 8):
        self._fast_mode = fast_mode
        self._face_cascade = None
        self._worker: Optional["FERWorker"] = None
        self._num_threads = num_threads
        self._window_size = window_size

    async def startup(self):
        try:
            import cv2
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
        except ImportError:
            pass

        if not self._fast_mode:
            from .deepface_worker import FERWorker
            self._worker = FERWorker(
                num_threads=self._num_threads,
                window_size=self._window_size,
            )
            self._worker.start()

    async def shutdown(self):
        if self._worker:
            self._worker.stop()
            self._worker = None

    async def health(self) -> ProviderStatus:
        ready = self._face_cascade is not None
        if self._worker:
            ready = ready and self._worker.is_running
        return ProviderStatus(
            name=self.name,
            ready=ready,
            error=None if ready else "FER not initialized",
        )

    async def predict_numpy(self, frame) -> FERResponse:
        try:
            import cv2
            import numpy as np
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            faces = self._face_cascade.detectMultiScale(gray, 1.1, 5) if self._face_cascade else []
            if len(faces) == 0:
                return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)
            if self._worker:
                emotion, confidence = self._worker.get_latest()
                mapped = EMOTION_MAP.get(emotion, emotion)
                x, y, w, h = faces[0]
                return FERResponse(emotion=mapped, confidence=confidence, face_detected=True, bounding_box=(int(x),int(y),int(w),int(h)))
            return FERResponse(emotion="neutral", confidence=0.0, face_detected=True)
        except Exception:
            return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)

    async def predict(self, frame_data: bytes) -> FERResponse:
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            faces = self._face_cascade.detectMultiScale(gray, 1.1, 5) if self._face_cascade else []

            if len(faces) == 0:
                return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)

            # Worker mode: enqueue raw JPEG bytes, return latest normalized emotion
            if self._worker:
                self._worker.enqueue_frame(frame_data)
                emotion, confidence = self._worker.get_latest()
                mapped = EMOTION_MAP.get(emotion, emotion)
                x, y, w, h = faces[0]
                return FERResponse(
                    emotion=mapped,
                    confidence=confidence,
                    face_detected=True,
                    bounding_box=(int(x), int(y), int(w), int(h)),
                )

            # Fallback: fast heuristic
            if self._fast_mode:
                face_area = faces[0][2] * faces[0][3]
                frame_area = frame.shape[0] * frame.shape[1]
                ratio = face_area / frame_area
                emotion = "anxious" if ratio > 0.15 else ("neutral" if ratio > 0.08 else "calm")
                return FERResponse(emotion=emotion, confidence=0.5, face_detected=True)

            # Direct DeepFace (no worker)
            from deepface import DeepFace
            result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, silent=True)
            if isinstance(result, list):
                result = result[0]
            emotion = result.get('dominant_emotion', 'neutral')
            confidence = result.get('emotion', {}).get(emotion, 0.5) / 100.0
            mapped = EMOTION_MAP.get(emotion, emotion)
            x, y, w, h = faces[0]
            return FERResponse(
                emotion=mapped,
                confidence=confidence,
                face_detected=True,
                bounding_box=(int(x), int(y), int(w), int(h)),
            )
        except Exception:
            return FERResponse(emotion="neutral", confidence=0.0, face_detected=False)

    @property
    def is_running(self):
        return self._worker is not None and self._worker.is_running
