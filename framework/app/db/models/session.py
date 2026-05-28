"""
Session Model
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time


@dataclass
class SessionModel:
    """Session database model"""
    id: str
    workspace_id: str
    user_id: str
    created_at: float
    last_active: float
    metadata: Optional[str] = None


class SessionRepository:
    """Repository for session operations"""

    def __init__(self, database):
        self._db = database

    def create(self, session: SessionModel) -> None:
        """Create a new session"""
        self._db.execute(
            """INSERT INTO sessions (id, workspace_id, user_id, created_at, last_active, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session.id, session.workspace_id, session.user_id,
             session.created_at, session.last_active, session.metadata)
        )

    def get(self, session_id: str) -> Optional[SessionModel]:
        """Get a session by ID"""
        row = self._db.fetchone(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        if row:
            return SessionModel(
                id=row["id"],
                workspace_id=row["workspace_id"],
                user_id=row["user_id"],
                created_at=row["created_at"],
                last_active=row["last_active"],
                metadata=row["metadata"]
            )
        return None

    def update_last_active(self, session_id: str) -> None:
        """Update last active time"""
        self._db.execute(
            "UPDATE sessions SET last_active = ? WHERE id = ?",
            (time.time(), session_id)
        )

    def delete(self, session_id: str) -> bool:
        """Delete a session"""
        self._db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return True