from fastapi import WebSocket
from typing import Dict, Set, Optional, Callable, Awaitable
import json
import asyncio

class ConnectionManager:
    """Manages WebSocket connections and message routing"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, Set[str]] = {}  # session_id -> set of websocket ids
        self._permission_responses: Dict[str, asyncio.Future] = {}  # request_id -> future for permission response

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    async def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # Remove from all sessions
        for session_id in self.sessions:
            self.sessions[session_id].discard(client_id)

    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to a specific client"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict, session_id: str = None):
        """Broadcast message to all clients in a session or all clients"""
        if session_id and session_id in self.sessions:
            # Send to all clients in the session
            for client_id in self.sessions[session_id]:
                if client_id in self.active_connections:
                    await self.active_connections[client_id].send_json(message)
        else:
            # Send to all connected clients
            for websocket in self.active_connections.values():
                await websocket.send_json(message)

    def join_session(self, client_id: str, session_id: str):
        """Add client to a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = set()
        self.sessions[session_id].add(client_id)

    def leave_session(self, client_id: str, session_id: str):
        """Remove client from a session"""
        if session_id in self.sessions:
            self.sessions[session_id].discard(client_id)

    async def handle_message(self, client_id: str, message: dict):
        """Route incoming messages to appropriate handlers"""
        event_type = message.get("type")

        handlers = {
            "join-session": self._handle_join_session,
            "leave-session": self._handle_leave_session,
            "send-to-agent": self._handle_send_to_agent,
            "create-task": self._handle_create_task,
            "agent-action": self._handle_agent_action,
            "permission-response": self._handle_permission_response,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(client_id, message)

    async def _handle_join_session(self, client_id: str, message: dict):
        """Handle join session event"""
        session_id = message.get("sessionId")
        if session_id:
            self.join_session(client_id, session_id)
            await self.send_personal_message(
                {"type": "notification", "message": f"Joined session {session_id}"},
                client_id
            )

    async def _handle_leave_session(self, client_id: str, message: dict):
        """Handle leave session event"""
        session_id = message.get("sessionId")
        if session_id:
            self.leave_session(client_id, session_id)
            await self.send_personal_message(
                {"type": "notification", "message": f"Left session {session_id}"},
                client_id
            )

    async def _handle_send_to_agent(self, client_id: str, message: dict):
        """Handle send to agent event"""
        agent_id = message.get("agentId")
        content = message.get("content")
        session_id = message.get("sessionId", "default")

        # 通知客户端开始处理
        await self.send_personal_message(
            {"type": "agent-status", "agentId": agent_id, "status": "thinking", "message": "Processing..."},
            client_id
        )

        try:
            # 调用MainAgent处理请求
            from app.agents.main_agent import MainAgent
            main_agent = MainAgent()

            # MainAgent的think方法会创建workspace并协作
            result = await main_agent.think(content)

            # 发送响应
            await self.send_personal_message(
                {
                    "type": "new-message",
                    "agentRole": "main",
                    "content": result,
                    "isUser": False
                },
                client_id
            )
        except Exception as e:
            # 发送错误信息
            await self.send_personal_message(
                {
                    "type": "new-message",
                    "agentRole": "system",
                    "content": f"Error processing request: {str(e)}",
                    "isUser": False
                },
                client_id
            )

        # 通知处理完成
        await self.send_personal_message(
            {"type": "agent-status", "agentId": agent_id, "status": "idle", "message": "Complete"},
            client_id
        )

    async def _handle_create_task(self, client_id: str, message: dict):
        """Handle create task event"""
        task = message.get("task")
        await self.broadcast(
            {"type": "task-updated", "task": task},
            None
        )

    async def _handle_agent_action(self, client_id: str, message: dict):
        """Handle agent action event"""
        agent_id = message.get("agentId")
        action = message.get("action")

        await self.broadcast(
            {"type": "agent-status", "agentId": agent_id, "action": action},
            None
        )

    async def _handle_permission_response(self, client_id: str, message: dict):
        """Handle permission response from client"""
        request_id = message.get("request_id")
        action = message.get("action")
        feedback = message.get("feedback")

        if request_id in self._permission_responses:
            future = self._permission_responses[request_id]
            if not future.done():
                future.set_result({
                    "action": action,
                    "feedback": feedback,
                    "request_id": request_id
                })
            del self._permission_responses[request_id]

    async def send_permission_request(
        self,
        request_id: str,
        tool_name: str,
        description: str,
        path: Optional[str],
        command: Optional[str],
        risk_level: str,
        session_id: str = None
    ):
        """Send a permission request to the frontend"""
        await self.broadcast(
            {
                "type": "permission-request",
                "request_id": request_id,
                "tool_name": tool_name,
                "description": description,
                "path": path,
                "command": command,
                "risk_level": risk_level,
                "options": [
                    {"value": "allow", "label": "允许"},
                    {"value": "deny", "label": "拒绝"},
                    {"value": "allow_always", "label": "始终允许", "keybinding": "a"},
                    {"value": "deny_always", "label": "始终拒绝", "keybinding": "d"}
                ]
            },
            session_id
        )

    async def wait_for_permission_response(self, request_id: str, timeout: float = 300.0) -> Optional[dict]:
        """Wait for a permission response from the frontend"""
        future = asyncio.Future()
        self._permission_responses[request_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            # Timeout - treat as deny
            return {"action": "deny", "request_id": request_id, "feedback": None}
        finally:
            if request_id in self._permission_responses:
                del self._permission_responses[request_id]

# Singleton instance
ws_manager = ConnectionManager()
