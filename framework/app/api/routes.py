"""
API Routes - Frontend Integration
Provides HTTP endpoints for the frontend
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

from app.query.engine import QueryEngine, Message, StreamEvent
from app.query.config import QueryConfig
from app.tools.registry import tool_registry

router = APIRouter(prefix="/api/v1")


class QueryRequest(BaseModel):
    messages: List[Dict[str, str]]
    system_prompt: str = "You are a helpful assistant."
    tools: List[Dict[str, Any]] = []
    config: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    events: List[Dict[str, Any]]
    success: bool


@router.post("/query")
async def query(request: QueryRequest):
    """
    Execute a query with the engine.
    """
    try:
        # Parse messages
        messages = [Message(role=m["role"], content=m["content"]) for m in request.messages]

        # Create query config
        config = QueryConfig()
        if request.config:
            for key, value in request.config.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Create engine
        engine = QueryEngine(workspace_path=".", config=config)

        # Execute query
        events = []
        async for event in engine.query(messages, request.system_prompt, request.tools):
            events.append({"type": event.type, "data": event.data})

        return QueryResponse(events=events, success=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """
    List all available tools.
    """
    tools = tool_registry.list_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "is_read_only": t.is_read_only
            }
            for t in tools
        ]
    }


@router.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"}


class TaskCreateRequest(BaseModel):
    task_type: str
    command: Optional[str] = None
    agent_type: Optional[str] = None
    agent_config: Optional[Dict[str, Any]] = None


@router.post("/tasks")
async def create_task(request: TaskCreateRequest):
    """
    Create a new task.
    """
    from app.tasks.registry import task_registry

    task_id = f"task_{id(request)}"

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Task creation endpoint - implement with task system"
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    Get task status.
    """
    return {
        "task_id": task_id,
        "status": "unknown",
        "message": "Task status endpoint - implement with task system"
    }


@router.post("/agents/spawn")
async def spawn_agent(config: Dict[str, Any]):
    """
    Spawn an agent.
    """
    return {
        "agent_id": f"agent_{id(config)}",
        "status": "spawned",
        "config": config
    }


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """
    Get agent status.
    """
    return {
        "agent_id": agent_id,
        "status": "unknown"
    }