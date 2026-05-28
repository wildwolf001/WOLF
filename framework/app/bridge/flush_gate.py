"""
Flush Gate
Controls queue emission during reconnection
"""
import asyncio
from typing import Optional, Any
from ..transports.base import StreamEvent


class FlushGate:
    """
    Flush gate that controls when queued events are sent.
    During reconnection, events queue up and are flushed in order.
    """

    def __init__(self, max_queue_size: int = 100):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._is_flushing = False
        self._is_closed = False

    @property
    def is_flushing(self) -> bool:
        return self._is_flushing

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    async def enqueue(self, event: StreamEvent) -> bool:
        """
        Add an event to the queue.
        Returns False if queue is full or closed.
        """
        if self._is_closed:
            return False

        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            return False

    async def flush(self, transport: Any) -> int:
        """
        Flush all queued events through the transport.
        Returns number of events flushed.
        """
        if self._is_flushing:
            return 0

        self._is_flushing = True
        flushed = 0

        try:
            while not self._queue.empty():
                try:
                    event = self._queue.get_nowait()
                    await transport.send(event)
                    flushed += 1
                except asyncio.QueueEmpty:
                    break
        finally:
            self._is_flushing = False

        return flushed

    def close(self) -> None:
        """Close the gate and discard queued events"""
        self._is_closed = True
        # Clear the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def reset(self) -> None:
        """Reset the gate state"""
        self._is_flushing = False
        self._is_closed = False
        self.close()