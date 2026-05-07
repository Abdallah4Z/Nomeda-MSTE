import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List


class EventType(Enum):
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    EMOTION_UPDATED = "emotion_updated"
    DISTRESS_UPDATED = "distress_updated"
    TTS_GENERATED = "tts_generated"
    ERROR = "error"


@dataclass
class Event:
    type: EventType
    data: Any = None
    session_id: str = ""


EventHandler = Callable[[Event], Any]


class EventBus:
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}

    def on(self, event_type: EventType, handler: EventHandler):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def off(self, event_type: EventType, handler: EventHandler):
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    async def emit(self, event: Event):
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if hasattr(result, '__await__'):
                    await result
            except Exception as e:
                print(f"Event handler error: {e}")

    def emit_sync(self, event: Event):
        for handler in self._handlers.get(event.type, []):
            try:
                handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")


event_bus = EventBus()
