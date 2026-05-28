"""
Bridge Session Runner
"""
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator

from .session import Session, BridgeSession
from .remote_bridge_core import RemoteBridgeCore
from .types import BridgeMessage
from ..transports.base import StreamEvent


class SessionRunner:
    """
    Runs a session, coordinating between transport and query engine.
    """

    def __init__(
        self,
        session: Session,
        bridge: RemoteBridgeCore
    ):
        self._session = session
        self._bridge = bridge
        self._running = False

    @property
    def session_id(self) -> str:
        return self._session.session_id

    async def start(self) -> None:
        """Start the session"""
        self._running = True

    async def stop(self) -> None:
        """Stop the session"""
        self._running = False

    async def run_query(
        self,
        query: str,
        system_prompt: str,
        tools: list[Dict[str, Any]]
    ) -> AsyncGenerator[BridgeMessage, None]:
        """Run a query and yield messages"""
        from ..query.engine import QueryEngine

        engine = QueryEngine(
            workspace_path=f"/workspace/{self._session.workspace_id}"
        )

        from ..query.engine import Message
        messages = [Message(role="user", content=query)]

        async for event in engine.query(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools
        ):
            # Convert StreamEvent to BridgeMessage
            yield BridgeMessage(
                type=event.type,
                data=event.data,
                session_id=self._session.session_id,
                timestamp=time.time()
            )

    async def run(self) -> None:
        """Main run loop"""
        await self.start()

        try:
            async for message in self._bridge.receive():
                # Process message
                if message.type == "query":
                    # Handle query
                    pass
                elif message.type == "cancel":
                    # Handle cancel
                    pass
        finally:
            await self.stop()


import time