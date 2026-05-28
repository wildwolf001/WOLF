"""
Bridge UI Callbacks
"""
from typing import Callable, Awaitable, Optional, Dict, Any


class BridgeUICallbacks:
    """
    Manages UI callbacks for bridge events.
    """

    def __init__(self):
        self._callbacks: Dict[str, Callable] = {}

    def register(self, event_type: str, callback: Callable) -> None:
        """Register a callback for an event type"""
        self._callbacks[event_type] = callback

    def unregister(self, event_type: str) -> None:
        """Unregister a callback"""
        if event_type in self._callbacks:
            del self._callbacks[event_type]

    async def dispatch(self, event_type: str, data: Dict[str, Any]) -> None:
        """Dispatch an event to its callback"""
        if event_type in self._callbacks:
            callback = self._callbacks[event_type]
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)


# Default UI callbacks

async def default_on_thinking_start(data: Dict[str, Any]) -> None:
    """Default handler for thinking_start"""
    pass


async def default_on_content(data: Dict[str, Any]) -> None:
    """Default handler for content"""
    text = data.get("text", "")
    print(text, end="", flush=True)


async def default_on_tool_start(data: Dict[str, Any]) -> None:
    """Default handler for tool_start"""
    tool = data.get("tool", "")
    print(f"\n[Calling tool: {tool}]", flush=True)


async def default_on_tool_result(data: Dict[str, Any]) -> None:
    """Default handler for tool_result"""
    tool = data.get("tool", "")
    success = data.get("success", True)
    print(f"[Tool {tool} completed: {'ok' if success else 'error'}]", flush=True)


async def default_on_error(data: Dict[str, Any]) -> None:
    """Default handler for error"""
    error = data.get("error", "Unknown error")
    print(f"\n[Error: {error}]", flush=True)


DEFAULT_UI_CALLBACKS = BridgeUICallbacks()
DEFAULT_UI_CALLBACKS.register("thinking_start", default_on_thinking_start)
DEFAULT_UI_CALLBACKS.register("content", default_on_content)
DEFAULT_UI_CALLBACKS.register("tool_start", default_on_tool_start)
DEFAULT_UI_CALLBACKS.register("tool_result", default_on_tool_result)
DEFAULT_UI_CALLBACKS.register("error", default_on_error)