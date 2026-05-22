from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
from app.api.routes import agents, tasks, sessions, documents, knowledge, teams, channels, skills, permissions, tools
from app.api.routes import memory
from app.api.routes.skill_matcher import router as skill_matcher_router
from app.api.routes.process import router as process_router
from app.api.routes.stream import router as stream_router
from app.api.routes.config import router as config_router
from app.api.routes.files import router as files_router
from app.ws.connection_manager import ConnectionManager
import os
import re

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("WOLF API starting up...")
    # Initialize permission service
    from app.services.permission_service import init_permission_service, permission_service

    # 设置原始工作目录为当前进程工作目录
    permission_service.set_original_cwd(os.getcwd())

    # 预先添加一些常见的父目录路径
    common_base_paths = [
        "E:/agent",
        "E:/ai",
        "E:/AFSIM",
        os.getcwd(),  # 当前工作目录
    ]
    for path in common_base_paths:
        if os.path.exists(path):
            permission_service.add_working_directory(path, "pre_configured")

    init_permission_service()
    yield
    # Shutdown
    print("WOLF API shutting down...")

app = FastAPI(title="WOLF API", version="1.0.0", lifespan=lifespan)

# WebSocket manager
ws_manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    client_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                event_type = message.get("type")

                if event_type == "send-to-agent":
                    # Process message through MainAgent (Claude Code style)
                    agent_id = message.get("agentId")
                    content = message.get("content")
                    session_id = message.get("sessionId", "default")

                    # Determine agent role from agent_id
                    role = agent_id.replace("-001", "") if agent_id else "main"

                    # Broadcast agent is working
                    await ws_manager.broadcast({
                        "type": "agent-status",
                        "agentId": agent_id or "main-001",
                        "status": "working"
                    }, session_id)

                    # Notify typing
                    await ws_manager.broadcast({
                        "type": "agent-typing",
                        "agentId": agent_id or "main-001"
                    }, session_id)

                    # Process through MainAgent
                    try:
                        from app.agents.main_agent import MainAgent
                        from app.services.permission_service import permission_service

                        # Extract all paths from message and add to permission service
                        path_pattern = r'[A-Za-z]:(?:[/\\][^\s\'"]*)?'
                        path_matches = re.findall(path_pattern, content)
                        for path_match in path_matches:
                            # 尝试添加路径到权限服务
                            permission_service.check_and_add_path(path_match)

                        # Extract work directory from message if explicitly specified
                        work_dir = None
                        path_match = re.search(r'[A-Za-z]:[/\\][^\s\'"]+', content)
                        if path_match:
                            potential_path = path_match.group()
                            # 检查路径是否存在
                            if os.path.exists(potential_path):
                                work_dir = potential_path
                            elif os.path.exists(os.path.dirname(potential_path)):
                                work_dir = os.path.dirname(potential_path)

                        # Create MainAgent with proper work directory
                        main_agent = MainAgent(work_directory=work_dir)

                        # Execute with MainAgent (单Agent直接执行模式)
                        result = await main_agent.think(content)

                        # Send response
                        await ws_manager.send_personal_message({
                            "type": "new-message",
                            "agentRole": role,
                            "content": result,
                            "isUser": False
                        }, client_id)

                    except Exception as e:
                        await ws_manager.send_personal_message({
                            "type": "new-message",
                            "agentRole": role,
                            "content": f"Error processing request: {str(e)}",
                            "isUser": False
                        }, client_id)

                    # Broadcast agent is idle
                    await ws_manager.broadcast({
                        "type": "agent-status",
                        "agentId": agent_id or "main-001",
                        "status": "idle"
                    }, session_id)

                elif event_type == "join-session":
                    session_id = message.get("sessionId")
                    if session_id:
                        ws_manager.join_session(client_id, session_id)
                        await ws_manager.send_personal_message({
                            "type": "notification",
                            "message": f"Joined session {session_id}"
                        }, client_id)

                elif event_type == "leave-session":
                    session_id = message.get("sessionId")
                    if session_id:
                        ws_manager.leave_session(client_id, session_id)

                elif event_type == "create-task":
                    task = message.get("task")
                    await ws_manager.broadcast({
                        "type": "task-updated",
                        "task": task
                    }, message.get("sessionId"))

                elif event_type == "process-request":
                    # Legacy handler - now redirects to MainAgent directly
                    # DEPRECATED: Use "send-to-agent" instead
                    content = message.get("message")
                    session_id = message.get("sessionId", "default")

                    # Broadcast working status
                    await ws_manager.broadcast({
                        "type": "agent-status",
                        "agentId": "main-001",
                        "status": "working"
                    }, session_id)

                    # Notify typing
                    await ws_manager.broadcast({
                        "type": "agent-typing",
                        "agentId": "main-001"
                    }, session_id)

                    try:
                        from app.agents.main_agent import MainAgent
                        main_agent = MainAgent()
                        result = await main_agent.think(content)

                        await ws_manager.send_personal_message({
                            "type": "new-message",
                            "agentRole": "main",
                            "content": result,
                            "isUser": False
                        }, client_id)

                    except Exception as e:
                        await ws_manager.send_personal_message({
                            "type": "new-message",
                            "agentRole": "main",
                            "content": f"Error processing request: {str(e)}",
                            "isUser": False
                        }, client_id)

                    # Broadcast idle status
                    await ws_manager.broadcast({
                        "type": "agent-status",
                        "agentId": "main-001",
                        "status": "idle"
                    }, session_id)

                else:
                    # Default handling
                    await ws_manager.handle_message(client_id, message)

            except json.JSONDecodeError:
                await ws_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON"
                }, client_id)

    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
# Documents API - disabled (frontend removed)
# app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(process_router, prefix="/api/process", tags=["process"])
app.include_router(stream_router, prefix="/api/stream", tags=["stream"])
app.include_router(config_router, prefix="/api/config", tags=["config"])
app.include_router(files_router, prefix="/api/files", tags=["files"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(skill_matcher_router, prefix="/api/skill-matcher", tags=["skill-matcher"])
app.include_router(permissions.router, prefix="/api/permissions", tags=["permissions"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])

@app.get("/")
async def root():
    return {"message": "WOLF AI Research Team Platform API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
