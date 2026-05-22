from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentBase(BaseModel):
    title: str
    content: Optional[str] = None
    type: Optional[str] = "doc"
    task_id: Optional[str] = None

class DocumentCreate(DocumentBase):
    created_by: str = "user"

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    version: Optional[int] = None

class DocumentResponse(DocumentBase):
    id: str
    version: int
    created_by: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
