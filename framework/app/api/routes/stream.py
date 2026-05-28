"""
SSE Stream Route
"""
import asyncio
import json
import time
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..models import QueryRequest, StreamResponse
from ...query.engine import QueryEngine, Message
from ...prompt.prompts import get_system_prompt_with_sections
from ...services.tools.streaming_tool_executor import StreamingToolExecutor
from ...utils.logging import get_logger
from ...bridge.session import BridgeSession

router = APIRouter()
logger = get_logger("stream")
_bridge_session = BridgeSession()

# Active engine registry for cancellation
_active_engines: dict = {}  # session_id -> QueryEngine


@router.post("/stream/cancel")
async def cancel_stream(session_id: str) -> dict:
    """Cancel an active stream for a session"""
    engine = _active_engines.pop(session_id, None)
    if engine and not engine.is_cancelled:
        await engine.cancel(reason="user_requested")
        logger.info(f"[Stream] Cancelled stream for session {session_id}")
        return {"status": "ok", "cancelled": True}
    return {"status": "not_found", "cancelled": False}


def format_sse_event(event_type: str, data: dict) -> str:
    """Format event as SSE"""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@router.get("/stream")
async def stream_endpoint(
    user_message: str,
    workspace_id: str = "default",
    session_id: str = None,
    history: str = None
) -> StreamingResponse:
    """
    SSE endpoint for streaming query responses.
    """
    logger.info(f"[Stream] GET /stream - user_message={user_message[:50]}..., workspace_id={workspace_id}, session_id={session_id}")

    async def event_generator() -> AsyncGenerator[bytes, None]:
        engine = QueryEngine(workspace_path=f"/workspace/{workspace_id}")
        _active_engines[session_id or "default"] = engine
        executor = StreamingToolExecutor()

        # Load session history if session_id provided
        messages = []
        if session_id:
            # Get or create session to ensure history storage exists
            session = _bridge_session.get_or_create_session(session_id, workspace_id, "default")
            session_history = _bridge_session.get_history(session_id)
            for msg in session_history:
                messages.append(Message(
                    role=msg["role"],
                    content=msg.get("content", ""),
                    tool_calls=msg.get("tool_calls"),
                    tool_call_id=msg.get("tool_call_id")
                ))
            logger.info(f"[Stream] Loaded {len(session_history)} session history messages")

        # Parse incoming history from URL parameter
        if history:
            try:
                import urllib.parse
                decoded_history = urllib.parse.unquote(history)
                incoming_history = json.loads(decoded_history)
                for msg in incoming_history:
                    messages.append(Message(role=msg.get("role", "user"), content=msg.get("content", "")))
                logger.info(f"[Stream] Added {len(incoming_history)} incoming history messages")
            except Exception as e:
                logger.error(f"[Stream] Failed to parse history: {e}")

        # Add current user message
        messages.append(Message(role="user", content=user_message))

        # Build system prompt
        system_prompt = get_system_prompt_with_sections(
            project_name=workspace_id
        )
        logger.info(f"[Stream] System prompt built, length: {len(system_prompt)}")

        # Get tool schemas from registry
        from ...tools import tool_registry
        tools = [t.to_dict() for t in tool_registry.list_tools()]
        logger.info(f"[Stream] Loaded {len(tools)} tools from registry")

        try:
            event_count = 0
            assistant_response = ""
            async for event in engine.query(
                messages=messages,
                system_prompt=system_prompt,
                tools=tools
            ):
                event_count += 1
                logger.debug(f"[Stream] Event {event_count}: type={event.type}, data={event.data}")

                # Track assistant content
                if event.type == "content":
                    assistant_response += event.data.get("text", "")

                # Convert event to SSE
                sse_data = format_sse_event(event.type, event.data)
                yield sse_data.encode()

                # Check for completion
                if event.type == "thinking_complete":
                    logger.info(f"[Stream] thinking_complete received, total events: {event_count}")
                    # Save FULL message history to session (including tool calls and tool results)
                    if session_id:
                        _bridge_session.clear_history(session_id)
                        for msg in messages:
                            _bridge_session.add_message(
                                session_id,
                                msg.role,
                                msg.content,
                                tool_calls=msg.tool_calls if hasattr(msg, 'tool_calls') else None,
                                tool_call_id=msg.tool_call_id if hasattr(msg, 'tool_call_id') else None
                            )
                        logger.info(f"[Stream] Saved {len(messages)} messages to session {session_id}")

                        # Auto-extract memories from conversation (LLM-driven, like cc-haha)
                        import os as _os
                        if _os.getenv('WOLF_AUTO_MEMORY', 'true').lower() != 'false':
                            try:
                                msgs_dict = [
                                    {"role": m.role, "content": m.content}
                                    for m in messages if m.role in ('user', 'assistant')
                                ]
                                saved = []
                                # Try LLM-driven extraction first
                                try:
                                    from ...memory.llm_extraction import get_llm_extraction_service
                                    llm_extractor = get_llm_extraction_service()
                                    saved = await llm_extractor.extract(msgs_dict, session_id)
                                except Exception as _llm_err:
                                    logger.debug(f"[Stream] LLM extraction failed, trying keyword fallback: {_llm_err}")
                                    # Fallback to keyword extraction
                                    try:
                                        from ...memory.extraction import get_memory_extraction_service
                                        kw_extractor = get_memory_extraction_service()
                                        saved = await kw_extractor.extract_and_save(msgs_dict)
                                    except Exception:
                                        pass

                                # Save session context bridge
                                try:
                                    from ...memory.session_bridge import get_session_bridge
                                    bridge = get_session_bridge()
                                    bridge.save_session_context(session_id, msgs_dict)
                                except Exception:
                                    pass

                                if saved:
                                    logger.info(f"[Stream] Auto-memory: saved {len(saved)} files: {saved}")
                                    sse_data = format_sse_event("memory_updated", {"files": len(saved)})
                                    yield sse_data.encode()
                            except Exception as e:
                                logger.debug(f"[Stream] Auto-memory skipped: {e}")
                    break

        except Exception as e:
            logger.error(f"[Stream] Exception in event_generator: {e}", exc_info=True)
            error_data = format_sse_event("error", {"error": str(e)})
            yield error_data.encode()
        finally:
            _active_engines.pop(session_id or "default", None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/stream")
async def stream_post_endpoint(
    request: QueryRequest,
    workspace_id: str = "default"
) -> StreamingResponse:
    """
    POST endpoint for streaming query responses.
    """
    logger.info(f"[Stream] POST /stream - message={request.message[:50]}..., workspace_id={workspace_id}")

    async def event_generator() -> AsyncGenerator[bytes, None]:
        engine = QueryEngine(workspace_path=f"/workspace/{workspace_id}")
        _active_engines[f"post_{workspace_id}"] = engine
        executor = StreamingToolExecutor()

        # Build messages with history
        messages = []
        if request.history:
            for msg in request.history:
                messages.append(Message(role=msg.role, content=msg.content))
        messages.append(Message(role="user", content=request.message))
        logger.info(f"[Stream] Messages built: {len(messages)} total")

        # Build system prompt
        system_prompt = get_system_prompt_with_sections(
            project_name=workspace_id
        )

        # Get tool schemas
        tools = []

        try:
            event_count = 0
            async for event in engine.query(
                messages=messages,
                system_prompt=system_prompt,
                tools=tools
            ):
                event_count += 1
                logger.debug(f"[Stream] Event {event_count}: type={event.type}")
                sse_data = format_sse_event(event.type, event.data)
                yield sse_data.encode()

                if event.type == "thinking_complete":
                    logger.info(f"[Stream] POST thinking_complete, total events: {event_count}")
                    break

        except Exception as e:
            logger.error(f"[Stream] POST Exception in event_generator: {e}", exc_info=True)
            error_data = format_sse_event("error", {"error": str(e)})
            yield error_data.encode()
        finally:
            _active_engines.pop(f"post_{workspace_id}", None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )