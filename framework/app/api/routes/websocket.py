"""
WebSocket Route
"""
import asyncio
import json
import time
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...query.engine import QueryEngine, Message
from ...prompt.prompts import get_system_prompt_with_sections
from ...utils.logging import get_logger
from ...bridge.session import BridgeSession

router = APIRouter()
logger = get_logger("websocket")
_bridge_session = BridgeSession()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for bidirectional communication.
    """
    logger.info("WebSocket connection opened")
    await websocket.accept()

    # Initialize query engine
    engine = QueryEngine(workspace_path="/workspace/default")
    session_id = f"ws_{int(time.time())}"
    logger.info(f"WebSocket session: {session_id}")

    try:
        while True:
            logger.debug("Waiting for WebSocket message...")
            # Receive message
            data = await websocket.receive_json()
            logger.debug(f"Received WebSocket message: {data}")

            msg_type = data.get("type", "query")
            logger.info(f"WebSocket msg_type: {msg_type}")
            logger.info(f"Full message data keys: {list(data.keys())}")

            # Extract data - differs by message type
            # For send-to-agent/process-request: {type, agentId, content, sessionId, history}
            # For query: {type, data: {message, workspace_id, ...}}
            if msg_type in ("send-to-agent", "process-request"):
                msg_data = data  # Data is at root level
            else:
                msg_data = data.get("data", {})

            if msg_type == "query" or msg_type == "send-to-agent" or msg_type == "process-request":
                user_message = msg_data.get("message", "") or msg_data.get("content", "")
                workspace_id = msg_data.get("workspace_id", "default")
                incoming_session_id = msg_data.get("session_id") or session_id
                incoming_history = msg_data.get("history", [])

                logger.info(f"Query: workspace={workspace_id}, session={incoming_session_id}, message={user_message[:100]}...")

                # Get or create session
                session = _bridge_session.get_or_create_session(incoming_session_id, workspace_id, "default")

                # Build messages: session history + incoming history + current message
                messages = []
                session_history = _bridge_session.get_history(incoming_session_id)

                # Add session history first (from previous websocket sessions)
                for msg in session_history:
                    messages.append(Message(
                        role=msg["role"],
                        content=msg.get("content", ""),
                        tool_calls=msg.get("tool_calls"),
                        tool_call_id=msg.get("tool_call_id")
                    ))

                # Add incoming history (from current page session)
                for msg in incoming_history:
                    messages.append(Message(role=msg.get("role", "user"), content=msg.get("content", "")))

                # Add current user message
                messages.append(Message(role="user", content=user_message))
                logger.info(f"WebSocket: {len(session_history)} session history + {len(incoming_history)} incoming history + 1 current")

                # Build system prompt
                system_prompt = get_system_prompt_with_sections(
                    project_name=workspace_id
                )
                logger.debug(f"System prompt built, length: {len(system_prompt)}")

                # Get tool schemas from registry (same as stream endpoint)
                from ...tools import tool_registry
                tools = [t.to_dict() for t in tool_registry.list_tools()]
                logger.info(f"[WebSocket] Loaded {len(tools)} tools from registry")

                # Process query
                event_count = 0
                assistant_response = ""
                async for event in engine.query(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=tools
                ):
                    event_count += 1
                    logger.debug(f"Event {event_count}: type={event.type}")

                    # Track assistant content
                    if event.type == "content":
                        assistant_response += event.data.get("text", "")

                    # Send event via WebSocket
                    await websocket.send_json({
                        "type": event.type,
                        "data": event.data
                    })

                    # Check for completion
                    if event.type == "thinking_complete":
                        logger.info(f"Query complete, total events: {event_count}")
                        # Save FULL message history to session (including tool calls and tool results)
                        _bridge_session.clear_history(incoming_session_id)
                        for msg in messages:
                            _bridge_session.add_message(
                                incoming_session_id,
                                msg.role,
                                msg.content,
                                tool_calls=msg.tool_calls if hasattr(msg, 'tool_calls') else None,
                                tool_call_id=msg.tool_call_id if hasattr(msg, 'tool_call_id') else None
                            )
                        logger.info(f"Saved {len(messages)} messages to session {incoming_session_id}")

                        # Auto-extract memories from conversation (LLM-driven)
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
                                except Exception:
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
                                    logger.info(f"[WS] Auto-memory: saved {len(saved)} files: {saved}")
                                    await websocket.send_json({
                                        "type": "memory_updated",
                                        "data": {"files": len(saved)}
                                    })
                            except Exception as e:
                                logger.debug(f"[WS] Auto-memory skipped: {e}")
                        break

            elif msg_type == "ping":
                logger.debug("Received ping, sending pong")
                await websocket.send_json({"type": "pong", "data": {}})

            elif msg_type == "join-session":
                session_id = msg_data.get("session_id", session_id)
                _bridge_session.get_or_create_session(session_id, "default", "websocket")
                logger.info(f"Joined session: {session_id}")
                await websocket.send_json({"type": "session-joined", "data": {"session_id": session_id}})

            elif msg_type == "leave-session":
                if session_id:
                    _bridge_session.leave_session(session_id)
                logger.info(f"Left session: {session_id}")

            elif msg_type == "cancel":
                logger.info("Received cancel request")
                engine.cancel()
                await websocket.send_json({
                    "type": "cancelled",
                    "data": {}
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"error": str(e)}
            })
        except Exception:
            pass
    finally:
        logger.info("WebSocket connection closed")