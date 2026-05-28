"""
Bridge Session Management — SQLite-backed persistence.
Survives restarts: sessions and message history are stored in wolf.db.
"""
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class Message:
    """Chat message for session history (supports OpenAI tool calling format)"""
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class Session:
    """Session information"""
    session_id: str
    workspace_id: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BridgeSession:
    """Session manager backed by SQLite (wolf.db). Survives restarts."""

    def __init__(self):
        self._db = None   # lazy init
        self._session_repo = None
        self._message_repo = None

    def _init(self):
        if self._db is not None:
            return
        from ..db.database import get_database
        from ..db.models.session import SessionModel, SessionRepository
        from ..db.models.message import MessageModel, MessageRepository
        self._db = get_database()
        self._session_repo = SessionRepository(self._db)
        self._message_repo = MessageRepository(self._db)

    def create_session(
        self, workspace_id: str, user_id: str, session_id: Optional[str] = None
    ) -> Session:
        self._init()
        from ..db.models.session import SessionModel
        if session_id is None:
            session_id = f"sess_{int(time.time())}_{user_id}"
        model = SessionModel(
            id=session_id, workspace_id=workspace_id, user_id=user_id,
            created_at=time.time(), last_active=time.time(), metadata="{}"
        )
        self._session_repo.create(model)
        return Session(session_id=session_id, workspace_id=workspace_id, user_id=user_id)

    def get_session(self, session_id: str) -> Optional[Session]:
        self._init()
        model = self._session_repo.get(session_id)
        if not model:
            return None
        return Session(
            session_id=model.id, workspace_id=model.workspace_id,
            user_id=model.user_id, created_at=model.created_at,
            last_active=model.last_active,
            metadata=json.loads(model.metadata) if model.metadata else {}
        )

    def update_session(self, session_id: str, **kwargs) -> bool:
        self._init()
        model = self._session_repo.get(session_id)
        if not model:
            return False
        self._session_repo.update_last_active(session_id)
        return True

    def delete_session(self, session_id: str) -> bool:
        self._init()
        self._message_repo.delete_by_session(session_id)
        return self._session_repo.delete(session_id)

    def list_sessions(self, workspace_id: Optional[str] = None) -> list[Session]:
        """List recent sessions"""
        self._init()
        from ..db.database import get_database
        rows = get_database().fetchall(
            "SELECT * FROM sessions ORDER BY last_active DESC LIMIT 50"
        )
        result = []
        for row in rows:
            if workspace_id and row["workspace_id"] != workspace_id:
                continue
            meta = row.get("metadata", "{}")
            result.append(Session(
                session_id=row["id"], workspace_id=row["workspace_id"],
                user_id=row["user_id"], created_at=row["created_at"],
                last_active=row["last_active"],
                metadata=json.loads(meta) if meta else {}
            ))
        return result

    def add_message(
        self, session_id: str, role: str, content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None
    ) -> bool:
        self._init()
        from ..db.models.message import MessageModel
        model = MessageModel(
            id=None, session_id=session_id, role=role, content=content,
            created_at=time.time(), tool_calls=tool_calls, tool_call_id=tool_call_id
        )
        self._message_repo.create(model)
        self._session_repo.update_last_active(session_id)
        return True

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        self._init()
        models = self._message_repo.get_by_session(session_id)
        return [
            {
                "id": m.id,
                "role": m.role, "content": m.content,
                "tool_calls": m.tool_calls,
                "tool_call_id": m.tool_call_id,
                "created_at": m.created_at
            }
            for m in models
        ]

    def delete_message(self, session_id: str, message_id: int) -> bool:
        """Delete a single message"""
        self._init()
        return self._message_repo.delete_by_id(message_id, session_id)

    def rollback_to(self, session_id: str, from_message_id: int) -> bool:
        """Delete all messages from the given ID onwards (rollback)"""
        self._init()
        self._message_repo.delete_from(session_id, from_message_id)
        return True

    def clear_history(self, session_id: str) -> bool:
        self._init()
        self._message_repo.delete_by_session(session_id)
        self._session_repo.update_last_active(session_id)
        return True

    def get_or_create_session(
        self, session_id: str, workspace_id: str = "default", user_id: str = "default"
    ) -> Session:
        existing = self.get_session(session_id)
        if existing:
            return existing
        return self.create_session(workspace_id=workspace_id, user_id=user_id, session_id=session_id)

    def leave_session(self, session_id: str) -> bool:
        """Leave a session (clear history but keep session record)"""
        return self.clear_history(session_id)
