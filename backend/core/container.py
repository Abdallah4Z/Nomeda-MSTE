from typing import Any, Dict, Optional, Type

from ..config import Settings
from ..providers.base import BaseProvider, ProviderRegistry
from ..providers.llm import LLMProvider
from ..providers.tts import TTSProvider
from ..providers.stt import STTProvider
from ..providers.ser import SERProvider
from ..providers.fer import FERProvider
from ..providers.rag import RAGProvider
from ..storage.base import SessionStore
from .events import EventBus
from .session import SessionManager
from .orchestrator import Orchestrator


class Container:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._providers: Dict[str, BaseProvider] = {}
        self._event_bus = EventBus()
        self._session_manager: Optional[SessionManager] = None
        self._orchestrator: Optional[Orchestrator] = None
        self._store: Optional[SessionStore] = None

    def register_provider(self, capability: str, provider: BaseProvider):
        self._providers[capability] = provider

    def get_provider(self, capability: str) -> Optional[BaseProvider]:
        return self._providers.get(capability)

    def get_llm(self) -> Optional[LLMProvider]:
        return self.get_provider("llm")

    def get_tts(self) -> Optional[TTSProvider]:
        return self.get_provider("tts")

    def get_stt(self) -> Optional[STTProvider]:
        return self.get_provider("stt")

    def get_ser(self) -> Optional[SERProvider]:
        return self.get_provider("ser")

    def get_fer(self) -> Optional[FERProvider]:
        return self.get_provider("fer")

    def get_rag(self) -> Optional[RAGProvider]:
        return self.get_provider("rag")

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def session_manager(self) -> Optional[SessionManager]:
        return self._session_manager

    @session_manager.setter
    def session_manager(self, sm: SessionManager):
        self._session_manager = sm

    @property
    def orchestrator(self) -> Optional[Orchestrator]:
        return self._orchestrator

    @orchestrator.setter
    def orchestrator(self, o: Orchestrator):
        self._orchestrator = o

    @property
    def store(self) -> Optional[SessionStore]:
        return self._store

    @store.setter
    def store(self, s: SessionStore):
        self._store = s

    @property
    def settings(self) -> Settings:
        return self._settings

    async def startup(self):
        for name, provider in self._providers.items():
            await provider.startup()

        if self._store:
            await self._store.startup()

    async def shutdown(self):
        for name, provider in self._providers.items():
            await provider.shutdown()

        if self._store:
            await self._store.shutdown()

    def all_provider_statuses(self) -> list[Dict[str, Any]]:
        statuses = []
        for name, provider in self._providers.items():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                status = loop.run_until_complete(provider.health())
                loop.close()
                statuses.append({
                    "name": name,
                    "status": "ready" if status.ready else "error",
                    "description": status.error or "",
                })
            except Exception:
                statuses.append({"name": name, "status": "error", "description": "Health check failed"})
        return statuses
