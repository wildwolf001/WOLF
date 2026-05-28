"""
API Request/Response Models
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class MessageCreate(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    workspace_id: str
    history: Optional[List[MessageCreate]] = []


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


class SessionCreate(BaseModel):
    workspace_id: str
    user_id: str


class ConfigUpdate(BaseModel):
    config: Dict[str, Any]


class StreamResponse(BaseModel):
    event: str
    data: Dict[str, Any]


class ErrorResponse(BaseModel):
    error: str
    code: int
    details: Optional[Dict[str, Any]] = None