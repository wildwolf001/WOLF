"""
Base Transport Abstract Class
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Dict, Any
import asyncio


class StreamEvent:
    """Represents a stream event"""

    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type = event_type
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "data": self.data}

    def __repr__(self):
        return f"StreamEvent(type={self.type}, data={self.data})"


class BaseTransport(ABC):
    """Abstract base class for all transports"""

    def __init__(self):
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 1.0

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection"""
        pass

    @abstractmethod
    async def send(self, event: StreamEvent) -> None:
        """Send an event"""
        pass

    @abstractmethod
    async def receive(self) -> AsyncGenerator[StreamEvent, None]:
        """Receive events as an async generator"""
        pass

    async def reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff"""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            return False

        self._reconnect_attempts += 1
        delay = self._reconnect_delay * (2 ** (self._reconnect_attempts - 1))
        await asyncio.sleep(delay)

        try:
            await self.disconnect()
            await self.connect()
            return True
        except Exception:
            return False

    def reset_reconnect(self) -> None:
        """Reset reconnect state"""
        self._reconnect_attempts = 0