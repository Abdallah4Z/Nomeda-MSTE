import threading
from typing import Any, Dict, Optional


class SystemState:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._data = {}
                    cls._instance._data_lock = threading.Lock()
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        with self._data_lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any):
        with self._data_lock:
            self._data[key] = value

    def update(self, data: Dict[str, Any]):
        with self._data_lock:
            self._data.update(data)

    def snapshot(self) -> Dict[str, Any]:
        with self._data_lock:
            return dict(self._data)

    def clear(self):
        with self._data_lock:
            self._data.clear()


system_state = SystemState()
