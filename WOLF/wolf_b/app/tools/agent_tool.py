"""
Agent Tool - Create and manage agents in the AI team
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

router = APIRouter()

# Agent storage
agents_db: Dict[str, dict] = {}


class AgentCreate(BaseModel):
    name: str
    role: str  # pm, coder, researcher, reviewer, etc.
    description: Optional[str] = ""
    capabilities: List[str] = []
    model: Optional[str] = "default"


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    status: Optional[str] = None


class Agent(BaseModel):
    id: str
    name: str
    role: str
    description: str
    capabilities: List[str]
    status: str  # idle, working, stopped
    created_at: str


@router.post("/agents")
async def create_agent(input: AgentCreate) -> Agent:
    """Create a new agent"""
    agent_id = f"agent-{uuid.uuid4().hex[:8]}"

    agent = {
        "id": agent_id,
        "name": input.name,
        "role": input.role,
        "description": input.description,
        "capabilities": input.capabilities,
        "model": input.model,
        "status": "idle",
        "created_at": datetime.now().isoformat(),
    }

    agents_db[agent_id] = agent
    return agent


@router.get("/agents")
async def list_agents(role: Optional[str] = None, status: Optional[str] = None) -> List[Agent]:
    """List all agents, optionally filtered"""
    agents = list(agents_db.values())

    if role:
        agents = [a for a in agents if a["role"] == role]
    if status:
        agents = [a for a in agents if a["status"] == status]

    return agents


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> Agent:
    """Get agent by ID"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents_db[agent_id]


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, updates: AgentUpdate) -> Agent:
    """Update an agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agents_db[agent_id]
    update_data = updates.model_dump(exclude_none=True)

    for key, value in update_data.items():
        agent[key] = value

    return agent


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str) -> dict:
    """Delete an agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    del agents_db[agent_id]
    return {"success": True, "message": "Agent deleted"}


@router.post("/agents/{agent_id}/message")
async def send_message_to_agent(agent_id: str, message: dict) -> dict:
    """Send a message to an agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agents_db[agent_id]
    agent["status"] = "working"

    # Store message
    msg_key = f"messages_{agent_id}"
    if msg_key not in agents_db:
        agents_db[msg_key] = []

    agents_db[msg_key].append({
        "content": message.get("content", ""),
        "timestamp": datetime.now().isoformat(),
        "direction": "incoming"
    })

    return {"success": True, "message": "Message sent"}


@router.get("/agents/{agent_id}/messages")
async def get_agent_messages(agent_id: str) -> List[dict]:
    """Get messages for an agent"""
    msg_key = f"messages_{agent_id}"
    return agents_db.get(msg_key, [])