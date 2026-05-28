"""
Stop Hooks
Allows stopping query execution based on conditions
"""
from typing import Callable, Awaitable, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class StopReason(Enum):
    """Reason for stopping"""
    COMPLETED = "completed"
    MAX_TURNS = "max_turns"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    HOOK = "hook"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class StopContext:
    """Context passed to stop hooks"""
    turn_count: int
    tool_results: List[Dict[str, Any]]
    token_usage: int
    error: Optional[str] = None


StopHook = Callable[[StopContext], Awaitable[Optional[StopReason]]]


class StopHookManager:
    """
    Manages stop hooks that can halt query execution.
    """

    def __init__(self):
        self._hooks: List[StopHook] = []

    def register_hook(self, hook: StopHook) -> None:
        """Register a stop hook"""
        self._hooks.append(hook)

    def unregister_hook(self, hook: StopHook) -> None:
        """Unregister a stop hook"""
        if hook in self._hooks:
            self._hooks.remove(hook)

    async def check_hooks(self, context: StopContext) -> Optional[StopReason]:
        """Check all hooks and return first stop reason"""
        for hook in self._hooks:
            try:
                reason = await hook(context)
                if reason is not None:
                    return reason
            except Exception:
                continue
        return None

    async def run_hooks(self, context: StopContext) -> Optional[StopReason]:
        """Run all hooks and return aggregate stop reason"""
        return await self.check_hooks(context)


# Built-in stop hooks

async def max_turns_hook(context: StopContext, max_turns: int = 10) -> Optional[StopReason]:
    """Stop after max turns reached"""
    if context.turn_count >= max_turns:
        return StopReason.MAX_TURNS
    return None


async def max_tokens_hook(context: StopContext, max_tokens: int = 8000) -> Optional[StopReason]:
    """Stop after max tokens exceeded"""
    if context.token_usage >= max_tokens:
        return StopReason.MAX_TOKENS
    return None


async def error_hook(context: StopContext) -> Optional[StopReason]:
    """Stop on error"""
    if context.error is not None:
        return StopReason.ERROR
    return None


# Global stop hook manager
_stop_hook_manager: Optional[StopHookManager] = None


def get_stop_hook_manager() -> StopHookManager:
    """Get the global stop hook manager"""
    global _stop_hook_manager
    if _stop_hook_manager is None:
        _stop_hook_manager = StopHookManager()
    return _stop_hook_manager