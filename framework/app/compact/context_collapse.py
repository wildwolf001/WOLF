"""
Context Collapse
Implements context compression when context exceeds limits
"""
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import re


@dataclass
class CollapsedContent:
    """Represents collapsed content"""
    original_length: int
    collapsed_length: int
    summary: str
    preserved_indices: List[int]


class ContextCollapser:
    """
    Collapses context when it exceeds token limits.
    Preserves important information while reducing context size.
    """

    def __init__(
        self,
        max_tokens: int = 100000,
        preserve_recent: int = 10,
        summary_fn: Optional[Callable[[str], str]] = None
    ):
        self._max_tokens = max_tokens
        self._preserve_recent = preserve_recent
        self._summary_fn = summary_fn or self._default_summary

    def _default_summary(self, content: str) -> str:
        """Default summary function - takes first N chars"""
        max_chars = 200
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "..."

    def collapse_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> CollapsedContent:
        """
        Collapse messages while preserving recent ones and key information.
        """
        if not messages:
            return CollapsedContent(0, 0, "", [])

        original_length = sum(len(str(m)) for m in messages)

        # Separate recent messages from older ones
        recent = messages[-self._preserve_recent:] if len(messages) > self._preserve_recent else messages
        older = messages[:-self._preserve_recent] if len(messages) > self._preserve_recent else []

        # Generate summary of older messages
        if older:
            older_text = "\n".join(str(m) for m in older)
            summary = self._summary_fn(older_text)
        else:
            summary = ""

        # Calculate collapsed result
        collapsed_messages = older + recent if older else recent
        collapsed_length = sum(len(str(m)) for m in collapsed_messages)

        return CollapsedContent(
            original_length=original_length,
            collapsed_length=collapsed_length,
            summary=summary,
            preserved_indices=list(range(len(collapsed_messages)))
        )

    def collapse_by_ratio(
        self,
        messages: List[Dict[str, Any]],
        ratio: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Collapse messages by keeping only a ratio of them.
        """
        if not messages or ratio >= 1.0:
            return messages

        keep_count = max(1, int(len(messages) * ratio))
        return messages[-keep_count:]


def collapse_conversation(
    messages: List[Dict[str, Any]],
    max_messages: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to collapse a conversation.
    """
    collapser = ContextCollapser()
    result = collapser.collapse_by_ratio(messages, ratio=0.5)
    return result