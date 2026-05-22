"""
Task Cancellation Service - Manage task cancellation tokens

This service provides:
1. Cancellation token management for running tasks
2. API endpoints to trigger cancellation
3. Periodic check mechanism during long-running operations
"""
import asyncio
import uuid
from typing import Optional, Set
from datetime import datetime


class CancellationToken:
    """Individual cancellation token for a task"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._cancelled = False
        self._created_at = datetime.now()

    def cancel(self):
        """Mark this token as cancelled"""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        """Check if this token has been cancelled"""
        return self._cancelled

    def __repr__(self):
        return f"CancellationToken(task_id={self.task_id}, cancelled={self._cancelled})"


class TaskCancellationService:
    """
    Service to manage task cancellation

    Usage:
    1. Before starting a task, create a token: token = cancellation_service.create_token(task_id)
    2. During long operations, periodically check: if token.is_cancelled: raise asyncio.CancelledError
    3. To cancel, call cancellation_service.cancel_task(task_id)
    4. After completion, clean up: cancellation_service.remove_token(task_id)
    """

    def __init__(self):
        self._tokens: Set[CancellationToken] = set()
        self._lock = asyncio.Lock()

    async def create_token(self, task_id: str) -> CancellationToken:
        """Create a cancellation token for a task"""
        async with self._lock:
            # Remove existing token for same task if any
            self._tokens = {t for t in self._tokens if t.task_id != task_id}
            token = CancellationToken(task_id)
            self._tokens.add(token)
            return token

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a specific task

        Returns True if task was found and cancelled, False otherwise
        """
        async with self._lock:
            for token in self._tokens:
                if token.task_id == task_id:
                    token.cancel()
                    return True
            return False

    async def cancel_all(self):
        """Cancel all running tasks"""
        async with self._lock:
            for token in self._tokens:
                token.cancel()

    async def remove_token(self, task_id: str):
        """Remove a token after task completion"""
        async with self._lock:
            self._tokens = {t for t in self._tokens if t.task_id != task_id}

    async def is_cancelled(self, task_id: str) -> bool:
        """Check if a specific task has been cancelled"""
        for token in self._tokens:
            if token.task_id == task_id:
                return token.is_cancelled
        return False

    def get_active_tasks(self) -> list:
        """Get list of active task IDs"""
        return [t.task_id for t in self._tokens if not t.is_cancelled]

    def get_cancelled_tasks(self) -> list:
        """Get list of cancelled task IDs"""
        return [t.task_id for t in self._tokens if t.is_cancelled]


# Global singleton instance
cancellation_service = TaskCancellationService()