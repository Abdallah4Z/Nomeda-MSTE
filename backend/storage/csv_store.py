import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import SessionStore


class CSVSessionStore(SessionStore):
    def __init__(self, sessions_dir: str = "data/sessions"):
        self._sessions_dir = sessions_dir
        os.makedirs(self._sessions_dir, exist_ok=True)

    async def startup(self) -> None:
        os.makedirs(self._sessions_dir, exist_ok=True)

    async def shutdown(self) -> None:
        pass

    async def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        filepath = os.path.join(self._sessions_dir, f"session_{session_id}.json")
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        csv_path = os.path.join(self._sessions_dir, "sessions.csv")
        is_new = not os.path.exists(csv_path)
        with open(csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["session_id", "timestamp", "duration", "emotion", "distress", "messages"])
            stats = data.get("stats", {})
            checkin = data.get("checkin", {}) or {}
            writer.writerow([
                session_id,
                data.get("timestamp", datetime.now().isoformat()),
                data.get("duration_seconds", 0),
                checkin.get("emotion", stats.get("dominant_emotion", "")),
                stats.get("avg_distress", ""),
                stats.get("message_count", 0),
            ])

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        filepath = os.path.join(self._sessions_dir, f"session_{session_id}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath) as f:
            return json.load(f)

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        sessions = []
        files = sorted(
            [f for f in os.listdir(self._sessions_dir) if f.endswith(".json")],
            reverse=True,
        )
        files = files[offset:offset + limit]
        for fname in files:
            filepath = os.path.join(self._sessions_dir, fname)
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    sessions.append({
                        "id": data.get("session_id", fname),
                        "timestamp": data.get("timestamp"),
                        "duration": data.get("duration_seconds"),
                        "emotion": data.get("checkin", {}).get("emotion") if data.get("checkin") else None,
                        "distress": data.get("stats", {}).get("avg_distress"),
                        "messages": data.get("stats", {}).get("message_count", 0),
                    })
            except Exception:
                pass
        return sessions

    async def get_total_count(self) -> int:
        return len([f for f in os.listdir(self._sessions_dir) if f.endswith(".json")])

    async def get_recent_sessions(self, limit: int = 5) -> List[Dict[str, Any]]:
        return await self.list_sessions(limit=limit)
