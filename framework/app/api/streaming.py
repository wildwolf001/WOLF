"""
Streaming API - SSE for frontend integration
"""
import asyncio
import json
from typing import AsyncGenerator, List, Dict, Any
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.query.engine import QueryEngine, Message, StreamEvent
from app.query.config import QueryConfig

router = APIRouter(prefix="/api/v1")


async def sse_event(event_type: str, data: Dict[str, Any]) -> bytes:
    """Format data as SSE event"""
    content = json.dumps({"type": event_type, "data": data})
    return f"data: {content}\n\n".encode("utf-8")


@router.post("/query/stream")
async def query_stream(request: dict):
    """
    Execute a query with streaming response (SSE).
    """
    messages = [Message(role=m["role"], content=m["content"]) for m in request.get("messages", [])]
    system_prompt = request.get("system_prompt", "You are helpful.")
    tools = request.get("tools", [])

    config = QueryConfig()

    async def event_stream():
        engine = QueryEngine(workspace_path=".", config=config)

        try:
            async for event in engine.query(messages, system_prompt, tools):
                yield await sse_event(event.type, event.data)
        except Exception as e:
            yield await sse_event("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/tasks/{task_id}/stream")
async def task_stream(task_id: str):
    """
    Stream task output via SSE.
    """
    async def task_event_stream():
        # Placeholder - would connect to actual task output
        yield f"data: {json.dumps({'type': 'started', 'data': {'task_id': task_id}})}\n\n".encode()
        yield f"data: {json.dumps({'type': 'progress', 'data': {'task_id': task_id, 'progress': 50}})}\n\n".encode()
        yield f"data: {json.dumps({'type': 'completed', 'data': {'task_id': task_id}})}\n\n".encode()

    return StreamingResponse(
        task_event_stream(),
        media_type="text/event-stream"
    )


@router.get("/events/stream")
async def events_stream():
    """
    General event stream for frontend updates.
    """
    async def event_generator():
        # Placeholder for real-time events
        await asyncio.sleep(1)
        yield f"data: {json.dumps({'type': 'heartbeat', 'data': {'timestamp': asyncio.get_event_loop().time()}})}\n\n".encode()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )