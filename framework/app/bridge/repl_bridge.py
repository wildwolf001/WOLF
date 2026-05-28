"""
REPL Bridge
"""
import asyncio
import json
from typing import Optional, Dict, Any, AsyncGenerator

from ..transports.base import StreamEvent


class REPLBridge:
    """
    REPL Bridge for interactive sessions.
    """

    def __init__(
        self,
        input_stream: asyncio.StreamReader,
        output_stream: asyncio.StreamWriter
    ):
        self._input = input_stream
        self._output = output_stream
        self._running = False

    async def start(self) -> None:
        """Start the REPL bridge"""
        self._running = True

    async def stop(self) -> None:
        """Stop the REPL bridge"""
        self._running = False

    async def send(self, event: StreamEvent) -> None:
        """Send an event"""
        data = json.dumps(event.to_dict()) + "\n"
        self._output.write(data.encode())
        await self._output.drain()

    async def receive(self) -> AsyncGenerator[StreamEvent, None]:
        """Receive events"""
        while self._running:
            line = await self._input.readline()
            if not line:
                break

            try:
                data = json.loads(line.decode())
                event = StreamEvent(
                    event_type=data.get("type", "message"),
                    data=data.get("data", data)
                )
                yield event
            except json.JSONDecodeError:
                continue

    async def run(self) -> None:
        """Main run loop"""
        await self.start()

        try:
            async for event in self.receive():
                # Process event and respond
                if event.type == "ping":
                    await self.send(StreamEvent("pong", {"status": "ok"}))
        finally:
            await self.stop()