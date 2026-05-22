from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Session as SessionModel
from app.db.schemas import SessionCreate, SessionResponse

router = APIRouter()

@router.get("", response_model=List[SessionResponse])
async def get_sessions(db: Session = Depends(get_db)):
    """Get all sessions"""
    sessions = db.query(SessionModel).all()
    return sessions

@router.post("", response_model=SessionResponse)
async def create_session(session: SessionCreate, db: Session = Depends(get_db)):
    """Create a new session"""
    session_id = f"session-{len(db.query(SessionModel).all()) + 1}"
    db_session = SessionModel(
        id=session_id,
        title=session.title,
        created_by=session.created_by
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get session by ID"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete session"""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}
