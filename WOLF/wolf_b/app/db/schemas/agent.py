from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AgentBase(BaseModel):
    role: str
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    capabilities: Optional[List[str]] = []

class AgentCreate(AgentBase):
    id: Optional[str] = None
    llm_provider: Optional[str] = None
    model: Optional[str] = None

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    status: Optional[str] = None
    current_task: Optional[str] = None
    capabilities: Optional[List[str]] = None

class AgentResponse(AgentBase):
    id: str
    role: str
    status: str
    current_task: Optional[str] = None
    llm_provider: Optional[str] = None
    model: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
