"""
Task Model
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskModel:
    """Task database model"""
    id: str
    session_id: str
    title: str
    status: str
    created_at: float
    completed_at: Optional[float] = None


class TaskRepository:
    """Repository for task operations"""

    def __init__(self, database):
        self._db = database

    def create(self, task: TaskModel) -> None:
        """Create a new task"""
        self._db.execute(
            """INSERT INTO tasks (id, session_id, title, status, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task.id, task.session_id, task.title, task.status,
             task.created_at, task.completed_at)
        )

    def get(self, task_id: str) -> Optional[TaskModel]:
        """Get a task by ID"""
        cursor = self._db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        )
        row = cursor.fetchone()
        if row:
            return TaskModel(
                id=row["id"],
                session_id=row["session_id"],
                title=row["title"],
                status=row["status"],
                created_at=row["created_at"],
                completed_at=row["completed_at"]
            )
        return None

    def update_status(self, task_id: str, status: str, completed_at: Optional[float] = None) -> None:
        """Update task status"""
        self._db.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, task_id)
        )

    def get_by_session(self, session_id: str) -> list[TaskModel]:
        """Get tasks for a session"""
        cursor = self._db.execute(
            "SELECT * FROM tasks WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,)
        )
        rows = cursor.fetchall()
        return [
            TaskModel(
                id=row["id"],
                session_id=row["session_id"],
                title=row["title"],
                status=row["status"],
                created_at=row["created_at"],
                completed_at=row["completed_at"]
            )
            for row in rows
        ]