import threading
from typing import Any, Dict


class RuntimeConfig:
    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {
            "rag.relevance_threshold": 1.0,
            "ws.push_interval_ms": 1000,
            "camera.frame_interval_ms": 100,
            "audio.chunk_size": 4096,
            "tts.auto_play": True,
            "tts.enabled": True,
            "fer.enabled": True,
            "ser.enabled": True,
            "avatar.enabled": True,
            "session.max_duration_min": 0,
            "emotion.history_max": 200,
            "timeline.max_points": 60,
            "face.anim_speed_ms": 700,
        }

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        with self._lock:
            if key not in self._data:
                return False
            self._data[key] = value
            return True

    def set_many(self, updates: Dict[str, Any]) -> Dict[str, bool]:
        results = {}
        with self._lock:
            for key, value in updates.items():
                if key in self._data:
                    self._data[key] = value
                    results[key] = True
                else:
                    results[key] = False
        return results

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    @property
    def rag_relevance_threshold(self) -> float:
        return float(self.get("rag.relevance_threshold", 1.0))

    @property
    def tts_auto_play(self) -> bool:
        return bool(self.get("tts.auto_play", True))
