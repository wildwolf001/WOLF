"""
REPL Bridge Transport
"""
import asyncio
import json
from typing import Optional

from ..transports.base import BaseTransport, StreamEvent


class REPLBridgeTransport(BaseTransport):
    """
    Transport for REPL bridge communication.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        super().__init__()
        self._reader = reader
        self._writer = writer

    async def connect(self) -> None:
        """Connect to the REPL"""
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from the REPL"""
        self._connected = False

    async def send(self, event: StreamEvent) -> None:
        """Send an event"""
        if not self._connected:
            raise ConnectionError("Not connected")

        data = json.dumps(event.to_dict()) + "\n"
        self._writer.write(data.encode())
        await self._writer.drain()

    async def receive(self) -> AsyncGenerator[StreamEvent, None]:
        """Receive events"""
        while self._connected:
            try:
                line = await asyncio.wait_for(
                    self._reader.readline(),
                    timeout=3.0
                )
                if not line:
                    break

                data = json.loads(line.decode())
                yield StreamEvent(
                    event_type=data.get("type", "message"),
                    data=data.get("data", data)
                )
            except asyncio.TimeoutError:
                # Send keepalive
                yield StreamEvent(
                    event_type="keepalive",
                    data={"timestamp": 0}
                )