"""
Hybrid Transport Implementation
WebSocket for reading, HTTP POST for batch writing
"""
import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional
from .base import BaseTransport, StreamEvent


class HybridTransport(BaseTransport):
    """
    Hybrid transport that uses WebSocket for receiving
    and HTTP POST for batch uploading events.
    """

    def __init__(
        self,
        ws_endpoint: str,
        http_endpoint: str,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__()
        self._ws_endpoint = ws_endpoint
        self._http_endpoint = http_endpoint
        self._headers = headers or {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._ws: Optional[Any] = None
        self._session: Optional[Any] = None
        self._heartbeat_interval = 30
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self) -> None:
        """Establish hybrid connection"""
        import aiohttp
        import websockets

        await super().connect()
        self._running = True
        self.reset_reconnect()

        # Create HTTP session
        self._session = aiohttp.ClientSession()

        # Connect WebSocket
        self._ws = await websockets.connect(
            self._ws_endpoint,
            extra_headers=self._headers
        )

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        self._connected = True

    async def disconnect(self) -> None:
        """Close connections"""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()

        if self._session:
            await self._session.close()

        self._connected = False

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats"""
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
        """Queue event for batch upload"""
        if not self._connected:
            raise ConnectionError("Not connected")
        await self._event_queue.put(event)

    async def _upload_batch(self, events: list[StreamEvent]) -> None:
        """Upload batch of events via HTTP POST"""
        if not self._session or not events:
            return

        payload = json.dumps([
            {"type": e.type, "data": e.data}
            for e in events
        ])

        async with self._session.post(
            self._http_endpoint,
            data=payload,
            headers={"Content-Type": "application/json"}
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Batch upload failed: {resp.status}")

    async def flush(self) -> None:
        """Flush queued events as a batch"""
        events = []
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                events.append(event)
            except asyncio.QueueEmpty:
                break

        if events:
            await self._upload_batch(events)

    async def receive(self) -> AsyncGenerator[StreamEvent, None]:
        """Receive events from WebSocket"""
        while self._running and self._connected:
            try:
                message = await self._ws.recv()
                data = json.loads(message)

                event_type = data.get("type", "message")
                event_data = data.get("data", data)

                if event_type == "pong":
                    continue

                yield StreamEvent(event_type=event_type, data=event_data)

            except asyncio.CancelledError:
                break
            except Exception:
                if self._running and not await self.reconnect():
                    self._running = False
                break

    async def send_batch(self, events: list[StreamEvent]) -> None:
        """Send batch of events via HTTP POST"""
        await self._upload_batch(events)


def create_hybrid_transport(
    ws_endpoint: str,
    http_endpoint: str,
    headers: Optional[Dict[str, str]] = None
) -> HybridTransport:
    """Factory function to create hybrid transport"""
    return HybridTransport(
        ws_endpoint=ws_endpoint,
        http_endpoint=http_endpoint,
        headers=headers
    )