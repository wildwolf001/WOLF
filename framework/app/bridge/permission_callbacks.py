"""
Bridge Permission Callbacks
"""
from typing import Callable, Awaitable, Optional, Dict, Any
from enum import Enum


class PermissionStatus(Enum):
    """Permission status"""
    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"


class BridgePermissionCallbacks:
    """
    Manages permission callbacks for bridge operations.
    """

    def __init__(self):
        self._callbacks: Dict[str, Callable] = {}

    def register(self, permission_type: str, callback: Callable) -> None:
        """Register a permission callback"""
        self._callbacks[permission_type] = callback

    async def request_permission(
        self,
        permission_type: str,
        context: Dict[str, Any]
    ) -> PermissionStatus:
        """Request a permission"""
        callback = self._callbacks.get(permission_type)
        if not callback:
            return PermissionStatus.DENIED

        if asyncio.iscoroutinefunction(callback):
            result = await callback(context)
        else:
            result = callback(context)

        if result is True:
            return PermissionStatus.GRANTED
        elif result is False:
            return PermissionStatus.DENIED
        else:
            return PermissionStatus.PENDING


# Built-in permission callbacks

async def file_write_permission(context: Dict[str, Any]) -> bool:
    """Check if file write is allowed"""
    path = context.get("path", "")
    # Add your permission logic here
    return True


async def bash_permission(context: Dict[str, Any]) -> bool:
    """Check if bash command is allowed"""
    command = context.get("command", "")
    # Add your permission logic here
    return True


async def network_permission(context: Dict[str, Any]) -> bool:
    """Check if network access is allowed"""
    url = context.get("url", "")
    # Add your permission logic here
    return True


# Global permission callbacks
_permission_callbacks = BridgePermissionCallbacks()
_permission_callbacks.register("file_write", file_write_permission)
_permission_callbacks.register("bash", bash_permission)
_permission_callbacks.register("network", network_permission)


def get_permission_callbacks() -> BridgePermissionCallbacks:
    """Get the global permission callbacks"""
    return _permission_callbacks