"""
Session Memory
Manages memory for a single session
"""
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class MemoryItem:
    """A single memory item"""
    id: str
    content: str
    type: str  # "message", "tool_call", "tool_result", "summary"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionMemory:
    """
    Manages memory for a session.
    Keeps track of messages, tool calls, and summaries.
    """

    def __init__(self, session_id: str):
        self._session_id = session_id
        self._items: List[MemoryItem] = []
        self._token_count: int = 0

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def item_count(self) -> int:
        return len(self._items)

    @property
    def token_count(self) -> int:
        return self._token_count

    def add_message(
        self,
        content: str,
        role: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryItem:
        """Add a message to memory"""
        item = MemoryItem(
            id=f"msg_{len(self._items)}",
            content=content,
            type=f"message_{role}",
            metadata=metadata or {}
        )
        self._items.append(item)
        self._token_count += self._estimate_tokens(content)
        return item

    def add_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryItem:
        """Add a tool call to memory"""
        content = f"Tool: {tool_name}({arguments})"
        item = MemoryItem(
            id=f"tool_{len(self._items)}",
            content=content,
            type="tool_call",
            metadata={**({"tool": tool_name}), **(metadata or {})}
        )
        self._items.append(item)
        self._token_count += self._estimate_tokens(content)
        return item

    def add_tool_result(
        self,
        tool_name: str,
        result: Any,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryItem:
        """Add a tool result to memory"""
        content = f"Result [{tool_name}]: {result}"
        item = MemoryItem(
            id=f"result_{len(self._items)}",
            content=content,
            type="tool_result",
            metadata={**({"tool": tool_name, "success": success}), **(metadata or {})}
        )
        self._items.append(item)
        self._token_count += self._estimate_tokens(str(result))
        return item

    def add_summary(self, summary: str, metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
        """Add a summary to memory"""
        item = MemoryItem(
            id=f"summary_{len(self._items)}",
            content=summary,
            type="summary",
            metadata=metadata or {}
        )
        self._items.append(item)
        self._token_count += self._estimate_tokens(summary)
        return item

    def get_recent(self, count: int = 10) -> List[MemoryItem]:
        """Get the N most recent items"""
        return self._items[-count:] if self._items else []

    def get_by_type(self, item_type: str) -> List[MemoryItem]:
        """Get all items of a specific type"""
        return [item for item in self._items if item.type.startswith(item_type)]

    def clear(self) -> None:
        """Clear all memory"""
        self._items.clear()
        self._token_count = 0

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation"""
        return len(text) // 4


import asyncio