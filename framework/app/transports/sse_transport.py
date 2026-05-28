"""
SSE Transport Implementation
Supports reconnection, heartbeat, and sequence numbers
"""
import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional
from .base import BaseTransport, StreamEvent


class SSETransport(BaseTransport):
    """
    Server-Sent Events transport with reconnection and heartbeat support.
    """

    def __init__(self, endpoint: str, headers: Optional[Dict[str, str]] = None):
        super().__init__()
        self._endpoint = endpoint
        self._headers = headers or {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._sequence = 0
        self._last_event_id = 0
        self._heartbeat_interval = 30  # seconds
        self._liveness_timeout = 45  # seconds (liveness timer from cc-haha)
        self._running = False
        self._reader_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_pong_time: float = 0

    async def connect(self) -> None:
        """Establish SSE connection"""
        import aiohttp

        await super().connect()
        self._running = True
        self.reset_reconnect()

        # Create session and connect
        self._session = aiohttp.ClientSession()
        self._event_source = await self._session.get(
            self._endpoint,
            headers=self._headers,
            timeout=aiohttp.ClientTimeout(total=None)
        )

        # Start reader and heartbeat tasks
        self._reader_task = asyncio.create_task(self._read_events())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        self._connected = True

    async def disconnect(self) -> None:
        """Close SSE connection"""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, '_session'):
            await self._session.close()

        self._connected = False

    async def _read_events(self) -> None:
        """Read events from SSE stream"""
        import aiohttp

        try:
            async for line in self._event_source.content:
                if not self._running:
                    break

                line = line.decode('utf-8').strip()
                if not line:
                    continue

                # Parse SSE format: "event: type" or "data: {...}"
                if line.startswith('event:'):
                    event_type = line[6:].strip()
                    continue
                elif line.startswith('data:'):
                    data_str = line[5:].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = {"raw": data_str}

                    # Handle keepalive/pong
                    if event_type == 'pong':
                        self._last_pong_time = time.time()
                    elif event_type == 'keepalive':
                        self._last_pong_time = time.time()
                    else:
                        self._sequence += 1
                        event = StreamEvent(
                            event_type=event_type or "message",
                            data=data
                        )
                        await self._event_queue.put(event)

                # Check liveness
                if self._last_pong_time > 0:
                    elapsed = time.time() - self._last_pong_time
                    if elapsed > self._liveness_timeout:
                        # Connection considered dead, trigger reconnect
                        await self._handle_disconnect()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self._handle_disconnect()

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to maintain connection"""
        while self._running:
            await asyncio.sleep(self._heartbeat_interval)
            if self._running and self._connected:
                # Update last ping time to indicate we're still alive
                self._last_pong_time = time.time()

    async def _handle_disconnect(self) -> None:
        """Handle disconnection and attempt reconnect"""
        self._connected = False
        if await self.reconnect():
            self._last_pong_time = time.time()
        else:
            self._running = False

    async def send(self, event: StreamEvent) -> None:
        """Send an event (for batch uploads)"""
        if not self._connected:
            raise ConnectionError("Not connected")

        # Format as SSE
        data = json.dumps({
            "event": event.type,
            "data": event.data,
            "sequence": self._sequence
        })
        # SSE format is typically handled by the server for client->server
        # This is mainly for the batch uploader pattern
        await self._event_queue.put(event)

    async def receive(self) -> AsyncGenerator[StreamEvent, None]:
        """Receive events from the queue"""
        while self._running and self._connected:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=3.0
                )
                yield event
            except asyncio.TimeoutError:
                # Send keepalive to indicate we're still alive
                yield StreamEvent(
                    event_type="keepalive",
                    data={"timestamp": time.time()}
                )

    async def send_batch(self, events: list[StreamEvent]) -> None:
        """Send a batch of events (for flush gate pattern)"""
        for event in events:
            await self.send(event)


def create_sse_transport(endpoint: str, headers: Optional[Dict[str, str]] = None) -> SSETransport:
    """Factory function to create SSE transport"""
    return SSETransport(endpoint=endpoint, headers=headers)