import threading
import queue
from collections import Counter
from typing import Optional, Tuple


class FERWorker:
    def __init__(self, num_threads: int = 2, window_size: int = 8):
        self._frame_queue: queue.Queue = queue.Queue(maxsize=60)
        self._num_threads = num_threads
        self._window_size = window_size
        self._threads: list[threading.Thread] = []
        self._stop_event = threading.Event()

        self._latest_emotion = "neutral"
        self._latest_confidence = 0.0
        self._lock = threading.Lock()

        self._window: list[str] = []
        self._session_counts: Counter = Counter()

    def start(self):
        self._stop_event.clear()
        for i in range(self._num_threads):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f"fer-{i}")
            t.start()
            self._threads.append(t)

    def stop(self):
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set()

    def enqueue_frame(self, frame_data: bytes):
        try:
            self._frame_queue.put(frame_data, timeout=0.5)
        except queue.Full:
            pass

    def get_latest(self) -> Tuple[str, float]:
        with self._lock:
            return self._latest_emotion, self._latest_confidence

    def get_session_dominant(self) -> Optional[str]:
        with self._lock:
            if not self._session_counts:
                return None
            return self._session_counts.most_common(1)[0][0]

    def reset_session(self):
        with self._lock:
            self._session_counts.clear()
            self._window.clear()

    def _worker_loop(self):
        import cv2
        import numpy as np

        while not self._stop_event.is_set():
            try:
                frame_data = self._frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                from deepface import DeepFace

                result = DeepFace.analyze(
                    frame,
                    actions=["emotion"],
                    enforce_detection=False,
                    silent=True,
                )
                if isinstance(result, list):
                    result = result[0]
                emotion = result.get("dominant_emotion", "neutral")
                probs = result.get("emotion", {})
                confidence = probs.get(emotion, 50.0) / 100.0

            except Exception:
                continue

            with self._lock:
                self._window.append(emotion)
                self._session_counts[emotion] += 1

                if len(self._window) >= self._window_size:
                    normalized = Counter(self._window).most_common(1)[0][0]
                    self._latest_emotion = normalized
                    self._latest_confidence = confidence
                    self._window.clear()
