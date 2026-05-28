"""
Working Memory
Manages short-term working memory during query execution
"""
import time
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class WorkingMemoryItem:
    """A working memory item"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None  # None = never expires


class WorkingMemory:
    """
    Manages short-term working memory.
    Used during query execution to track intermediate state.
    """

    def __init__(self, ttl: float = 3600.0):  # 1 hour default TTL
        self._ttl = ttl
        self._items: Dict[str, WorkingMemoryItem] = {}
        self._access_order: List[str] = []  # LRU tracking

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in working memory"""
        expires = time.time() + (ttl or self._ttl) if ttl or self._ttl > 0 else None
        item = WorkingMemoryItem(key=key, value=value, expires_at=expires)
        self._items[key] = item

        # Update LRU order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from working memory"""
        item = self._items.get(key)
        if not item:
            return default

        # Check expiry
        if item.expires_at and time.time() > item.expires_at:
            del self._items[key]
            self._access_order.remove(key)
            return default

        # Update LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        return item.value

    def delete(self, key: str) -> bool:
        """Delete a value from working memory"""
        if key in self._items:
            del self._items[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False

    def has(self, key: str) -> bool:
        """Check if a key exists and is not expired"""
        item = self._items.get(key)
        if not item:
            return False
        if item.expires_at and time.time() > item.expires_at:
            self.delete(key)
            return False
        return True

    def clear(self) -> None:
        """Clear all working memory"""
        self._items.clear()
        self._access_order.clear()

    def keys(self) -> List[str]:
        """Get all keys"""
        self._cleanup_expired()
        return list(self._items.keys())

    def _cleanup_expired(self) -> None:
        """Remove expired items"""
        now = time.time()
        expired = [k for k, item in self._items.items()
                   if item.expires_at and now > item.expires_at]
        for k in expired:
            self.delete(k)

    def get_lru_order(self, count: int = 10) -> List[str]:
        """Get the N least recently used keys"""
        return self._access_order[:count]


# Global working memory
_working_memory: Optional[WorkingMemory] = None


def get_working_memory() -> WorkingMemory:
    """Get the global working memory"""
    global _working_memory
    if _working_memory is None:
        _working_memory = WorkingMemory()
    return _working_memory