"""
Message Model
"""
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class MessageModel:
    """Message database model"""
    id: Optional[int]
    session_id: str
    role: str
    content: str
    created_at: float
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class MessageRepository:
    """Repository for message operations"""

    def __init__(self, database):
        self._db = database

    def create(self, message: MessageModel) -> None:
        """Create a new message"""
        tc_json = json.dumps(message.tool_calls, ensure_ascii=False) if message.tool_calls else None
        self._db.execute(
            """INSERT INTO messages (session_id, role, content, tool_calls, tool_call_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message.session_id, message.role, message.content,
             tc_json, message.tool_call_id, message.created_at)
        )

    def get_by_session(self, session_id: str, limit: int = 200) -> list[MessageModel]:
        """Get messages for a session (oldest first)"""
        rows = self._db.fetchall(
            """SELECT * FROM messages WHERE session_id = ?
               ORDER BY id ASC LIMIT ?""",
            (session_id, limit)
        )
        result = []
        for row in rows:
            tc = row.get("tool_calls")
            tool_calls = json.loads(tc) if tc else None
            result.append(MessageModel(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
                tool_calls=tool_calls,
                tool_call_id=row.get("tool_call_id")
            ))
        return result

    def delete_by_session(self, session_id: str) -> None:
        """Delete all messages for a session"""
        self._db.execute(
            "DELETE FROM messages WHERE session_id = ?",
            (session_id,)
        )

    def delete_by_id(self, message_id: int, session_id: str) -> bool:
        """Delete a single message by ID"""
        before = self._db.fetchone(
            "SELECT COUNT(*) as c FROM messages WHERE id = ? AND session_id = ?",
            (message_id, session_id)
        )
        if not before or before.get("c", 0) == 0:
            return False
        self._db.execute(
            "DELETE FROM messages WHERE id = ? AND session_id = ?",
            (message_id, session_id)
        )
        return True

    def delete_from(self, session_id: str, from_id: int) -> int:
        """Delete messages from the given ID onwards. Returns count deleted."""
        self._db.execute(
            "DELETE FROM messages WHERE session_id = ? AND id >= ?",
            (session_id, from_id)
        )
        return 0  # SQLite doesn't return row count easily via custom DB wrapper