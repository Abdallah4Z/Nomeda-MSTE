import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schemas.session import CheckinData
from ..schemas.emotion import EmotionPoint
from ..storage.base import SessionStore
from .events import EventBus, Event, EventType
from .state import system_state


class SessionManager:
    def __init__(self, store: SessionStore, event_bus: EventBus):
        self._store = store
        self._event_bus = event_bus
        self._current_session_id: Optional[str] = None
        self._start_time: Optional[float] = None
        self._messages: List[Dict[str, Any]] = []
        self._emotion_history: List[EmotionPoint] = []
        self._checkin: Optional[CheckinData] = None

    @property
    def is_running(self) -> bool:
        return self._current_session_id is not None

    @property
    def session_id(self) -> Optional[str]:
        return self._current_session_id

    @property
    def start_time(self) -> Optional[float]:
        return self._start_time

    @property
    def messages(self) -> List[Dict[str, Any]]:
        return self._messages

    @property
    def emotion_history(self) -> List[EmotionPoint]:
        return self._emotion_history

    @property
    def checkin(self) -> Optional[CheckinData]:
        return self._checkin

    def start(self, checkin: Optional[CheckinData] = None) -> str:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        self._current_session_id = session_id
        self._start_time = datetime.now(timezone.utc).timestamp()
        self._messages = []
        self._emotion_history = []
        self._checkin = checkin

        system_state.set("session_id", session_id)
        system_state.set("running", True)

        self._event_bus.emit_sync(Event(
            type=EventType.SESSION_STARTED,
            data={"session_id": session_id, "checkin": checkin},
            session_id=session_id,
        ))
        return session_id

    async def end(self) -> Dict[str, Any]:
        if not self._current_session_id:
            return {}

        session_id = self._current_session_id
        duration = 0
        if self._start_time:
            duration = int(datetime.now(timezone.utc).timestamp() - self._start_time)

        summary = {
            "session_id": session_id,
            "duration_seconds": duration,
            "checkin": self._checkin.model_dump() if self._checkin else None,
            "messages": self._messages,
            "emotion_timeline": [p.model_dump() for p in self._emotion_history],
            "stats": self._calc_stats(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await self._store.save_session(session_id, summary)

        system_state.set("running", False)
        system_state.set("session_id", None)

        self._event_bus.emit_sync(Event(
            type=EventType.SESSION_ENDED,
            data=summary,
            session_id=session_id,
        ))

        self._current_session_id = None
        self._start_time = None
        return summary

    def add_message(self, role: str, text: str, **kwargs):
        msg = {
            "role": role,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        self._messages.append(msg)

        self._event_bus.emit_sync(Event(
            type=EventType.MESSAGE_RECEIVED if role == "user" else EventType.MESSAGE_SENT,
            data=msg,
            session_id=self._current_session_id or "",
        ))

    def add_emotion_point(self, face: Optional[str] = None, voice: Optional[str] = None, distress: int = 0, confidence: float = 0.0):
        point = EmotionPoint(
            time=datetime.now(timezone.utc).timestamp(),
            face=face,
            voice=voice,
            distress=distress,
            confidence=confidence,
        )
        self._emotion_history.append(point)

        update = {}
        if face is not None:
            update["video_emotion"] = face
        if voice is not None:
            update["voice_emotion"] = voice
        update["distress"] = distress
        system_state.update(update)

        self._event_bus.emit_sync(Event(
            type=EventType.EMOTION_UPDATED,
            data=point,
            session_id=self._current_session_id or "",
        ))

    def get_conversation_history(self, max_exchanges: int = 10, current_text: str = "") -> list[dict]:
        history = []
        for msg in self._messages:
            role = msg.get("role", "")
            text = msg.get("text", "")
            if role == "user" and text == current_text:
                continue
            if role in ("user", "ai"):
                history.append({"role": "user" if role == "user" else "assistant", "content": text})
        if len(history) > max_exchanges * 2:
            history = history[-(max_exchanges * 2):]
        return history

    def _calc_stats(self) -> Dict[str, Any]:
        user_msgs = [m for m in self._messages if m.get("role") == "user"]
        dists = [p.distress for p in self._emotion_history if p.distress is not None]
        avg_dist = round(sum(dists) / len(dists)) if dists else 0

        counts = {}
        for p in self._emotion_history:
            if p.face and p.face.lower() != "idle":
                counts[p.face] = counts.get(p.face, 0) + 1
        dominant = max(counts, key=counts.get) if counts else None

        return {
            "message_count": len(user_msgs),
            "avg_distress": avg_dist,
            "dominant_emotion": dominant,
        }

    def get_duration_seconds(self) -> int:
        if not self._start_time:
            return 0
        return int(datetime.now(timezone.utc).timestamp() - self._start_time)

    async def get_summary(self) -> Dict[str, Any]:
        if not self._current_session_id:
            return {}
        return {
            "session_id": self._current_session_id,
            "duration_seconds": self.get_duration_seconds(),
            "checkin": self._checkin.model_dump() if self._checkin else None,
            "messages": self._messages,
            "emotion_timeline": [p.model_dump() for p in self._emotion_history],
            "stats": self._calc_stats(),
        }
