from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = "medium"
    assignee_id: Optional[str] = None
    dependencies: Optional[List[str]] = []

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    parent_id: Optional[str] = None

class TaskAssign(BaseModel):
    assignee_id: str

class TaskResponse(TaskBase):
    id: str
    status: str
    parent_id: Optional[str] = None
    created_by: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
