"""
Bridge Main
Main bridge logic and coordination
"""
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator, Callable, Awaitable

from .config import BridgeConfig, DEFAULT_BRIDGE_CONFIG
from .remote_bridge_core import RemoteBridgeCore
from .types import BridgeMessage
from ..transports.base import StreamEvent


class BridgeMain:
    """
    Main bridge coordinator.
    Manages the connection lifecycle and coordinates components.
    """

    def __init__(self, config: Optional[BridgeConfig] = None):
        self._config = config or DEFAULT_BRIDGE_CONFIG
        self._bridge: Optional[RemoteBridgeCore] = None
        self._running = False

    @property
    def is_connected(self) -> bool:
        return self._bridge is not None and self._bridge.is_connected

    async def connect(
        self,
        workspace_id: str,
        user_id: str,
        token: Optional[str] = None
    ) -> None:
        """Connect to the bridge"""
        self._bridge = RemoteBridgeCore(config=self._config)
        await self._bridge.connect(workspace_id, user_id, token)
        self._running = True

    async def disconnect(self) -> None:
        """Disconnect from the bridge"""
        self._running = False
        if self._bridge:
            await self._bridge.disconnect()

    async def send_message(self, message: BridgeMessage) -> None:
        """Send a message through the bridge"""
        if not self._bridge:
            return

        event = StreamEvent(
            event_type=message.type,
            data=message.data
        )
        await self._bridge.send(event)

    async def receive_messages(
        self,
        filter_types: Optional[list[str]] = None
    ) -> AsyncGenerator[BridgeMessage, None]:
        """Receive messages from the bridge"""
        if not self._bridge:
            return

        async for message in self._bridge.receive():
            if filter_types and message.type not in filter_types:
                continue
            yield message

    async def send_batch(self, messages: list[BridgeMessage]) -> None:
        """Send multiple messages"""
        if not self._bridge:
            return

        events = [
            StreamEvent(event_type=m.type, data=m.data)
            for m in messages
        ]
        await self._bridge.send_batch(events)

    def get_epoch(self) -> int:
        """Get current epoch"""
        if self._bridge:
            return self._bridge.get_epoch()
        return 0


# Convenience functions

async def send_thinking_start(session_id: str) -> BridgeMessage:
    """Create a thinking_start message"""
    return BridgeMessage(
        type="thinking_start",
        data={"session_id": session_id},
        session_id=session_id
    )


async def send_content(text: str, session_id: str) -> BridgeMessage:
    """Create a content message"""
    return BridgeMessage(
        type="content",
        data={"text": text},
        session_id=session_id
    )


async def send_tool_start(
    tool: str,
    arguments: Dict[str, Any],
    session_id: str
) -> BridgeMessage:
    """Create a tool_start message"""
    return BridgeMessage(
        type="tool_start",
        data={"tool": tool, "arguments": arguments},
        session_id=session_id
    )