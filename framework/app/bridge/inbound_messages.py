"""
Inbound Messages Handler
"""
import json
from typing import Dict, Any, Optional, Callable
from .types import BridgeMessage
from .messaging import BridgeMessaging


class InboundMessages:
    """
    Handles inbound messages from the bridge.
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a message type"""
        self._handlers[message_type] = handler

    async def handle_message(self, message: BridgeMessage) -> None:
        """Handle an inbound message"""
        handler = self._handlers.get(message.type)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                await handler(message.data)
            else:
                handler(message.data)

    async def handle_raw(self, raw: Dict[str, Any]) -> None:
        """Handle raw message data"""
        message = BridgeMessaging.parse_inbound(raw)
        if message:
            await self.handle_message(message)


import asyncio