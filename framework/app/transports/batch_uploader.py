"""
Serial Batch Event Uploader
Batches events and uploads them in sequence
"""
import asyncio
import json
from typing import List, Optional, Callable, Awaitable
from .base import StreamEvent


class SerialBatchEventUploader:
    """
    Batches events and uploads them in serial sequence.
    Ensures ordered delivery of events.
    """

    def __init__(
        self,
        upload_endpoint: str,
        batch_size: int = 10,
        flush_interval: float = 0.5,
        headers: Optional[dict] = None
    ):
        self._upload_endpoint = upload_endpoint
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._headers = headers or {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._session: Optional[Any] = None
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the uploader"""
        import aiohttp
        self._session = aiohttp.ClientSession()
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Stop the uploader and flush remaining events"""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Flush remaining events
        await self._flush()

        if self._session:
            await self._session.close()

    async def enqueue(self, event: StreamEvent) -> None:
        """Add an event to the upload queue"""
        await self._queue.put(event)

    async def _flush_loop(self) -> None:
        """Periodically flush the queue"""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self._flush()

    async def _flush(self) -> None:
        """Flush events in batches"""
        events = []
        while not self._queue.empty() and len(events) < self._batch_size:
            try:
                event = self._queue.get_nowait()
                events.append(event)
            except asyncio.QueueEmpty:
                break

        if events and self._session:
            await self._upload_batch(events)

    async def _upload_batch(self, events: List[StreamEvent]) -> None:
        """Upload a batch of events"""
        if not self._session:
            return

        payload = json.dumps([
            {"type": e.type, "data": e.data}
            for e in events
        ])

        try:
            async with self._session.post(
                self._upload_endpoint,
                data=payload,
                headers={**self._headers, "Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Batch upload failed: {resp.status}")
        except Exception:
            # Re-queue events on failure
            for event in events:
                await self._queue.put(event)

    async def upload_immediate(self, event: StreamEvent) -> None:
        """Immediately upload a single event"""
        if not self._session:
            return

        payload = json.dumps([{"type": event.type, "data": event.data}])

        async with self._session.post(
            self._upload_endpoint,
            data=payload,
            headers={**self._headers, "Content-Type": "application/json"}
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Immediate upload failed: {resp.status}")