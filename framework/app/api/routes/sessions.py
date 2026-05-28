"""
Sessions Route
"""
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException

from ...bridge.session import Session, BridgeSession
from ..models import SessionCreate
from ...utils.logging import get_logger

router = APIRouter()
logger = get_logger("sessions")

# In-memory session store (would be database in production)
_session_store: Dict[str, Session] = {}
_bridge_session = BridgeSession()


@router.post("/sessions")
async def create_session(request: SessionCreate) -> dict:
    """Create a new session"""
    session = _bridge_session.create_session(
        workspace_id=request.workspace_id,
        user_id=request.user_id
    )
    _session_store[session.session_id] = session

    return {
        "session_id": session.session_id,
        "workspace_id": session.workspace_id,
        "user_id": session.user_id,
        "created_at": session.created_at
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get session info"""
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "workspace_id": session.workspace_id,
        "user_id": session.user_id,
        "created_at": session.created_at,
        "last_active": session.last_active,
        "metadata": session.metadata
    }


@router.get("/sessions")
async def list_sessions(workspace_id: Optional[str] = None) -> dict:
    """List all sessions"""
    sessions = _bridge_session.list_sessions(workspace_id)
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "workspace_id": s.workspace_id,
                "user_id": s.user_id,
                "last_active": s.last_active
            }
            for s in sessions
        ]
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Delete a session"""
    if session_id in _session_store:
        del _session_store[session_id]
        _bridge_session.delete_session(session_id)
        return {"status": "ok"}

    raise HTTPException(status_code=404, detail="Session not found")


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    updates: dict
) -> dict:
    """Update session metadata"""
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    _bridge_session.update_session(session_id, **updates)

    return {"status": "ok"}


@router.delete("/sessions/{session_id}/messages/{message_id}")
async def delete_message(session_id: str, message_id: int) -> dict:
    """Delete a single message from session history"""
    deleted = _bridge_session.delete_message(session_id, message_id)
    if deleted:
        return {"status": "ok", "deleted": True}
    raise HTTPException(status_code=404, detail="Message not found")


@router.post("/sessions/{session_id}/rollback")
async def rollback_session(session_id: str, from_message_id: int) -> dict:
    """Rollback session history to before the given message ID"""
    _bridge_session.rollback_to(session_id, from_message_id)
    return {"status": "ok", "rolled_back": True}


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str) -> dict:
    """Get session messages with IDs"""
    messages = _bridge_session.get_history(session_id)
    return {"session_id": session_id, "messages": messages}
