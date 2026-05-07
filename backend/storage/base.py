from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SessionStore(ABC):
    @abstractmethod
    async def startup(self) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass

    @abstractmethod
    async def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_total_count(self) -> int:
        pass

    @abstractmethod
    async def get_recent_sessions(self, limit: int = 5) -> List[Dict[str, Any]]:
        pass
