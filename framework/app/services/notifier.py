"""
Notifier Service
Sends notifications to users
"""
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """A notification"""
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: Optional[Dict[str, Any]] = None


class NotifierService:
    """
    Service for sending notifications.
    """

    def __init__(self):
        self._handlers: List[Callable] = []

    def register_handler(self, handler: Callable) -> None:
        """Register a notification handler"""
        self._handlers.append(handler)

    async def send(self, notification: Notification) -> bool:
        """Send a notification"""
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(notification)
                else:
                    handler(notification)
            except Exception:
                continue
        return True

    async def send_batch(self, notifications: List[Notification]) -> int:
        """Send multiple notifications"""
        sent = 0
        for notification in notifications:
            if await self.send(notification):
                sent += 1
        return sent


# Notification formatters

def format_tool_notification(tool_name: str, status: str) -> Notification:
    """Format a tool-related notification"""
    return Notification(
        title=f"Tool: {tool_name}",
        body=f"Tool execution {status}",
        priority=NotificationPriority.NORMAL
    )


def format_error_notification(error: str) -> Notification:
    """Format an error notification"""
    return Notification(
        title="Error",
        body=error,
        priority=NotificationPriority.HIGH
    )


def format_session_notification(session_id: str, action: str) -> Notification:
    """Format a session-related notification"""
    return Notification(
        title="Session Update",
        body=f"Session {session_id}: {action}",
        priority=NotificationPriority.LOW
    )


# Global notifier service
_notifier_service: Optional[NotifierService] = None


def get_notifier_service() -> NotifierService:
    """Get the global notifier service"""
    global _notifier_service
    if _notifier_service is None:
        _notifier_service = NotifierService()
    return _notifier_service