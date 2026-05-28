"""
Bridge API
"""
from typing import Dict, Any, Optional


class BridgeApi:
    """API client for bridge operations"""

    def __init__(self, endpoint: str, headers: Optional[Dict[str, str]] = None):
        self._endpoint = endpoint
        self._headers = headers or {}

    async def create_session(self, workspace_id: str, user_id: str) -> Dict[str, Any]:
        """Create a new session"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._endpoint}/sessions",
                json={"workspace_id": workspace_id, "user_id": user_id},
                headers=self._headers
            ) as resp:
                return await resp.json()

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session info"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._endpoint}/sessions/{session_id}",
                headers=self._headers
            ) as resp:
                return await resp.json()

    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update session metadata"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{self._endpoint}/sessions/{session_id}",
                json=updates,
                headers=self._headers
            ) as resp:
                return await resp.json()

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self._endpoint}/sessions/{session_id}",
                headers=self._headers
            ) as resp:
                return resp.status == 200