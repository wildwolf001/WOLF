"""
API Dependencies
"""
from typing import Optional
from fastapi import Depends, HTTPException, Header
from ..bridge.remote_bridge_core import RemoteBridgeCore, get_bridge


async def get_current_session(
    authorization: Optional[str] = Header(None)
) -> str:
    """Get current session from authorization header"""
    if not authorization:
        return "anonymous"

    if authorization.startswith("Bearer "):
        token = authorization[7:]
        # Extract session from token
        return token.split("_")[1] if "_" in token else "anonymous"

    return "anonymous"


async def get_workspace_id(
    workspace_id: Optional[str] = None
) -> str:
    """Get workspace ID"""
    if not workspace_id:
        return "default"
    return workspace_id


def get_query_config():
    """Get query configuration"""
    from ..query.config import DEFAULT_QUERY_CONFIG
    return DEFAULT_QUERY_CONFIG