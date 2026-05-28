"""
State Uploader
Uploads worker state periodically
"""
import asyncio
import json
from typing import Optional, Dict, Any


class StateUploader:
    """
    Uploads worker state to the server periodically.
    Used for tracking task progress and status.
    """

    def __init__(
        self,
        endpoint: str,
        upload_interval: float = 5.0,
        headers: Optional[Dict[str, str]] = None
    ):
        self._endpoint = endpoint
        self._upload_interval = upload_interval
        self._headers = headers or {}
        self._session: Optional[Any] = None
        self._state: Dict[str, Any] = {}
        self._running = False
        self._upload_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the state uploader"""
        import aiohttp
        self._session = aiohttp.ClientSession()
        self._running = True
        self._upload_task = asyncio.create_task(self._upload_loop())

    async def stop(self) -> None:
        """Stop the state uploader"""
        self._running = False

        if self._upload_task:
            self._upload_task.cancel()
            try:
                await self._upload_task
            except asyncio.CancelledError:
                pass

        # Final upload
        await self._upload_state()

        if self._session:
            await self._session.close()

    async def _upload_loop(self) -> None:
        """Periodically upload state"""
        while self._running:
            await asyncio.sleep(self._upload_interval)
            await self._upload_state()

    async def update_state(self, state: Dict[str, Any]) -> None:
        """Update the current state"""
        self._state.update(state)

    async def _upload_state(self) -> None:
        """Upload current state to server"""
        if not self._session or not self._state:
            return

        try:
            async with self._session.post(
                self._endpoint,
                json=self._state,
                headers={**self._headers, "Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    pass  # Silent failure for state uploads
        except Exception:
            pass

    def get_state(self) -> Dict[str, Any]:
        """Get current state"""
        return self._state.copy()