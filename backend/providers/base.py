from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type


@dataclass
class ProviderStatus:
    name: str
    ready: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def health(self) -> ProviderStatus:
        ...

    async def startup(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass


Capability = str

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[Capability, Dict[str, Type[BaseProvider]]] = {}

    def register(self, capability: Capability, key: str, provider_cls: Type[BaseProvider]):
        if capability not in self._providers:
            self._providers[capability] = {}
        self._providers[capability][key] = provider_cls

    def get(self, capability: Capability, key: str) -> Optional[Type[BaseProvider]]:
        return self._providers.get(capability, {}).get(key)

    def list_capabilities(self) -> Dict[Capability, list[str]]:
        return {cap: list(provs.keys()) for cap, provs in self._providers.items()}


registry = ProviderRegistry()
