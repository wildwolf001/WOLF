from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MessageBase(BaseModel):
    from_agent_id: str
    to_agent_id: Optional[str] = None
    content: str
    type: Optional[str] = "task"
    task_id: Optional[str] = None
    session_id: Optional[str] = None

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: str
    metadata: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
