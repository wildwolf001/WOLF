from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SessionBase(BaseModel):
    title: str

class SessionCreate(SessionBase):
    created_by: str = "user"

class SessionResponse(SessionBase):
    id: str
    created_by: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
