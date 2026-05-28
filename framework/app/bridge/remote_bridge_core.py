"""
Remote Bridge Core
Core bridge component with JWT refresh, epoch handling, and reconnection
"""
import asyncio
import json
import time
from typing import Optional, Dict, Any, AsyncGenerator, Callable, Awaitable
from .config import BridgeConfig, RemoteBridgeConfig, DEFAULT_BRIDGE_CONFIG
from .jwt_utils import decode_jwt, is_token_expired, create_access_token, create_refresh_token
from .flush_gate import FlushGate
from .types import BridgeMessage, BridgeEventType
from ..transports.base import StreamEvent, BaseTransport


class RemoteBridgeCore:
    """
    Core remote bridge with automatic reconnection and token refresh.
    """

    def __init__(
        self,
        config: Optional[BridgeConfig] = None,
        transport: Optional[BaseTransport] = None
    ):
        self._config = config or DEFAULT_BRIDGE_CONFIG
        self._transport = transport
        self._flush_gate = FlushGate(max_queue_size=self._config.flush_gate_max_size)

        self._session_id: Optional[str] = None
        self._user_id: Optional[str] = None
        self._workspace_id: Optional[str] = None

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0

        self._epoch: int = 0
        self._last_pong_time: float = 0
        self._connected = False
        self._running = False

        self._reconnect_task: Optional[asyncio.Task] = None
        self._refresh_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    async def connect(
        self,
        workspace_id: str,
        user_id: str,
        initial_token: Optional[str] = None
    ) -> None:
        """Connect to the remote bridge"""
        self._workspace_id = workspace_id
        self._user_id = user_id
        self._session_id = f"session_{int(time.time())}"

        if initial_token:
            self._access_token = initial_token
            self._token_expires_at = decode_jwt(initial_token).get("exp", 0)

        # Initialize transport if not provided
        if not self._transport:
            from ..transports.sse_transport import create_sse_transport
            endpoint = f"{self._config.api_endpoint}/stream?workspace_id={workspace_id}"
            self._transport = create_sse_transport(endpoint, self._get_headers())

        # Connect transport
        await self._transport.connect()
        self._connected = True
        self._running = True
        self._last_pong_time = time.time()

        # Start background tasks
        self._refresh_task = asyncio.create_task(self._token_refresh_loop())
        self._reconnect_task = asyncio.create_task(self._liveness_check())

    async def disconnect(self) -> None:
        """Disconnect from the remote bridge"""
        self._running = False

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._transport:
            await self._transport.disconnect()

        self._connected = False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with auth token"""
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _token_refresh_loop(self) -> None:
        """Periodically refresh the access token"""
        while self._running:
            # Calculate time until refresh needed
            if self._token_expires_at > 0:
                time_until_refresh = self._token_expires_at - time.time() - self._config.refresh_before
                if time_until_refresh > 0:
                    await asyncio.sleep(min(time_until_refresh, 60))
                else:
                    await self._refresh_token()
            else:
                await asyncio.sleep(60)

    async def _refresh_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self._refresh_token:
            return False

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._config.auth_endpoint}/refresh",
                    json={"refresh_token": self._refresh_token}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._access_token = data.get("access_token")
                        self._refresh_token = data.get("refresh_token", self._refresh_token)
                        self._token_expires_at = data.get("expires_at", time.time() + 3600)
                        return True
        except Exception:
            pass

        return False

    async def _liveness_check(self) -> None:
        """Check liveness and trigger reconnect if needed"""
        while self._running:
            await asyncio.sleep(self._config.liveness_timeout)
            if not self._running:
                break

            elapsed = time.time() - self._last_pong_time
            if elapsed > self._config.liveness_timeout:
                # Connection considered dead
                await self._handle_disconnect()

    async def _handle_disconnect(self) -> None:
        """Handle disconnection and reconnect"""
        self._connected = False
        self._epoch += 1

        # Try to reconnect with exponential backoff
        delay = self._config.reconnect_base_delay
        for attempt in range(self._config.max_reconnect_attempts):
            if not self._running:
                break

            await asyncio.sleep(min(delay, self._config.reconnect_max_delay))
            delay *= 2

            try:
                if self._transport:
                    await self._transport.disconnect()
                    await self._transport.connect()
                    self._last_pong_time = time.time()
                    self._connected = True

                    # Flush queued events
                    await self._flush_gate.flush(self._transport)
                    return
            except Exception:
                continue

        # Failed to reconnect
        self._running = False

    async def send(self, event: StreamEvent) -> None:
        """Send an event through the bridge"""
        if not self._connected:
            # Queue event for flush
            await self._flush_gate.enqueue(event)
            return

        try:
            await self._transport.send(event)
        except Exception:
            # Queue for later flush
            await self._flush_gate.enqueue(event)

    async def receive(self) -> AsyncGenerator[BridgeMessage, None]:
        """Receive messages from the bridge"""
        if not self._transport:
            return

        async for event in self._transport.receive():
            self._last_pong_time = time.time()

            if event.type == "pong":
                continue

            yield BridgeMessage(
                type=event.type,
                data=event.data,
                session_id=self._session_id,
                timestamp=time.time()
            )

    async def send_batch(self, events: list[StreamEvent]) -> None:
        """Send a batch of events"""
        for event in events:
            await self.send(event)

    def get_epoch(self) -> int:
        """Get current epoch number"""
        return self._epoch


# Global bridge instance
_bridge_instance: Optional[RemoteBridgeCore] = None


def get_bridge() -> RemoteBridgeCore:
    """Get the global bridge instance"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = RemoteBridgeCore()
    return _bridge_instance


async def create_bridge(
    workspace_id: str,
    user_id: str,
    token: Optional[str] = None,
    config: Optional[BridgeConfig] = None
) -> RemoteBridgeCore:
    """Factory function to create and connect a bridge"""
    bridge = RemoteBridgeCore(config=config)
    await bridge.connect(workspace_id, user_id, token)
    return bridge