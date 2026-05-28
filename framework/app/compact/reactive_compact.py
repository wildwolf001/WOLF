"""
Reactive Context Compaction
Automatically triggers compaction based on context growth
"""
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class CompactionTrigger:
    """Represents a compaction trigger event"""
    reason: str
    timestamp: float
    context_size: int
    threshold: int


class ReactiveCompactor:
    """
    Automatically triggers context compaction when thresholds are exceeded.
    """

    def __init__(
        self,
        token_threshold: int = 80000,
        message_count_threshold: int = 50,
        time_threshold: float = 300.0
    ):
        self._token_threshold = token_threshold
        self._message_count_threshold = message_count_threshold
        self._time_threshold = time_threshold

        self._last_compaction: float = 0
        self._compaction_count: int = 0
        self._triggers: List[CompactionTrigger] = []

    @property
    def should_compact(self) -> bool:
        """Check if compaction should be triggered"""
        return len(self._triggers) > self._compaction_count

    def check_context(
        self,
        token_count: int,
        message_count: int
    ) -> Optional[CompactionTrigger]:
        """
        Check context and return trigger if threshold exceeded.
        """
        reasons = []

        if token_count >= self._token_threshold:
            reasons.append(f"token_limit ({token_count} >= {self._token_threshold})")

        if message_count >= self._message_count_threshold:
            reasons.append(f"message_count ({message_count} >= {self._message_count_threshold})")

        if self._last_compaction > 0:
            elapsed = time.time() - self._last_compaction
            if elapsed >= self._time_threshold:
                reasons.append(f"time_threshold ({elapsed:.0f}s >= {self._time_threshold}s)")

        if reasons:
            trigger = CompactionTrigger(
                reason=", ".join(reasons),
                timestamp=time.time(),
                context_size=token_count,
                threshold=self._token_threshold
            )
            self._triggers.append(trigger)
            return trigger

        return None

    def record_compaction(self) -> None:
        """Record that compaction was performed"""
        self._last_compaction = time.time()
        self._compaction_count += 1

    def get_triggers(self) -> List[CompactionTrigger]:
        """Get all triggers"""
        return self._triggers.copy()

    def reset(self) -> None:
        """Reset the compactor state"""
        self._last_compaction = 0
        self._compaction_count = 0
        self._triggers = []


# Global reactive compactor
_reactive_compactor: Optional[ReactiveCompactor] = None


def get_reactive_compactor() -> ReactiveCompactor:
    """Get the global reactive compactor"""
    global _reactive_compactor
    if _reactive_compactor is None:
        _reactive_compactor = ReactiveCompactor()
    return _reactive_compactor