"""
WebSocket Transport Implementation
Supports heartbeat and reconnection
"""
import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional
from .base import BaseTransport, StreamEvent


class WebSocketTransport(BaseTransport):
    """
    WebSocket transport with heartbeat support.
    """

    def __init__(self, endpoint: str, headers: Optional[Dict[str, str]] = None):
        super().__init__()
        self._endpoint = endpoint
        self._headers = headers or {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._heartbeat_interval = 30  # seconds
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        self._ws: Optional[Any] = None

    async def connect(self) -> None:
        """Establish WebSocket connection"""
        import websockets

        await super().connect()
        self._running = True
        self.reset_reconnect()

        self._ws = await websockets.connect(
            self._endpoint,
            extra_headers=self._headers
        )

        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        self._connected = True

    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()

        self._connected = False

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping heartbeats"""
        while self._running:
            await asyncio.sleep(self._heartbeat_interval)
            if self._running and self._connected and self._ws:
                try:
                    await self._ws.send(json.dumps({
                        "type": "ping",
                        "timestamp": time.time()
                    }))
                except Exception:
                    self._running = False
                    break

    async def send(self, event: StreamEvent) -> None:
        """Send an event via WebSocket"""
        if not self._connected or not self._ws:
            raise ConnectionError("Not connected")

        data = json.dumps({
            "type": event.type,
            "data": event.data
        })
        await self._ws.send(data)

    async def receive(self) -> AsyncGenerator[StreamEvent, None]:
        """Receive events from WebSocket"""
        while self._running and self._connected:
            try:
                message = await self._ws.recv()
                data = json.loads(message)

                event_type = data.get("type", "message")
                event_data = data.get("data", data)

                # Handle pong
                if event_type == "pong":
                    continue

                yield StreamEvent(event_type=event_type, data=event_data)

            except asyncio.CancelledError:
                break
            except Exception:
                if self._running:
                    # Try to reconnect
                    if not await self.reconnect():
                        self._running = False
                break

    async def send_batch(self, events: list[StreamEvent]) -> None:
        """Send a batch of events"""
        for event in events:
            await self.send(event)


def create_websocket_transport(endpoint: str, headers: Optional[Dict[str, str]] = None) -> WebSocketTransport:
    """Factory function to create WebSocket transport"""
    return WebSocketTransport(endpoint=endpoint, headers=headers)