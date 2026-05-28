"""
CCR Client
Client for Cloud Code Runtime communication
"""
import asyncio
import json
from typing import Optional, Dict, Any


class CCRClient:
    """
    Client for communicating with the Cloud Code Runtime (CCR).
    Handles task distribution and result collection.
    """

    def __init__(self, endpoint: str, headers: Optional[Dict[str, str]] = None):
        self._endpoint = endpoint
        self._headers = headers or {}
        self._session: Optional[Any] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to CCR"""
        import aiohttp
        self._session = aiohttp.ClientSession()
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from CCR"""
        if self._session:
            await self._session.close()
        self._connected = False

    async def submit_task(self, task_data: Dict[str, Any]) -> str:
        """Submit a task and return task ID"""
        if not self._session:
            raise ConnectionError("Not connected")

        async with self._session.post(
            f"{self._endpoint}/tasks",
            json=task_data,
            headers=self._headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Task submission failed: {resp.status}")
            result = await resp.json()
            return result.get("task_id")

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        if not self._session:
            raise ConnectionError("Not connected")

        async with self._session.get(
            f"{self._endpoint}/tasks/{task_id}",
            headers=self._headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Task status failed: {resp.status}")
            return await resp.json()

    async def get_task_result(self, task_id: str) -> Any:
        """Get task result"""
        if not self._session:
            raise ConnectionError("Not connected")

        async with self._session.get(
            f"{self._endpoint}/tasks/{task_id}/result",
            headers=self._headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Task result failed: {resp.status}")
            return await resp.json()

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if not self._session:
            raise ConnectionError("Not connected")

        async with self._session.delete(
            f"{self._endpoint}/tasks/{task_id}",
            headers=self._headers
        ) as resp:
            return resp.status == 200