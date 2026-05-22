"""
REPL Tool - Interactive code execution environment
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

router = APIRouter()

# Session storage for REPL sessions
sessions_db: Dict[str, dict] = {}


class REPLSession(BaseModel):
    session_id: str
    language: str  # python, javascript, etc.
    context: Dict[str, Any] = {}
    history: List[dict] = []


class REPLExecute(BaseModel):
    code: str
    session_id: Optional[str] = None
    language: str = "python"


class REPLCreate(BaseModel):
    language: str = "python"
    context: Optional[Dict[str, Any]] = None


@router.post("/repl/sessions")
async def create_repl_session(input: REPLCreate) -> REPLSession:
    """Create a new REPL session"""
    session_id = f"repl-{uuid.uuid4().hex[:8]}"

    session = {
        "session_id": session_id,
        "language": input.language,
        "context": input.context or {},
        "history": [],
        "created_at": datetime.now().isoformat()
    }

    sessions_db[session_id] = session
    return session


@router.get("/repl/sessions/{session_id}")
async def get_repl_session(session_id: str) -> REPLSession:
    """Get a REPL session by ID"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="REPL session not found")
    return sessions_db[session_id]


@router.post("/repl/execute")
async def execute_repl(input: REPLExecute) -> dict:
    """Execute code in a REPL session"""
    from app.tools.code_execution_sandbox import execute_code

    # Get or create session
    session_id = input.session_id or f"repl-{uuid.uuid4().hex[:8]}"
    if session_id not in sessions_db:
        sessions_db[session_id] = {
            "session_id": session_id,
            "language": input.language,
            "context": {},
            "history": [],
            "created_at": datetime.now().isoformat()
        }

    session = sessions_db[session_id]

    # Execute code
    result = await execute_code(input.code, input.language)

    # Add to history
    history_entry = {
        "code": input.code,
        "output": result.get("output", ""),
        "error": result.get("error", ""),
        "timestamp": datetime.now().isoformat()
    }
    session["history"].append(history_entry)

    return {
        "session_id": session_id,
        "language": input.language,
        "output": result.get("output", ""),
        "error": result.get("error", ""),
        "success": result.get("success", False)
    }


@router.get("/repl/sessions/{session_id}/history")
async def get_repl_history(session_id: str) -> List[dict]:
    """Get execution history for a REPL session"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="REPL session not found")
    return sessions_db[session_id]["history"]


@router.delete("/repl/sessions/{session_id}")
async def delete_repl_session(session_id: str) -> dict:
    """Delete a REPL session"""
    if session_id in sessions_db:
        del sessions_db[session_id]
    return {"success": True, "message": "REPL session deleted"}