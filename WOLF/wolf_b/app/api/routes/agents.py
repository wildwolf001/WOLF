from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Agent
from app.db.schemas import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()

# Default agents configuration - Single agent mode (multi-agent deprecated)
DEFAULT_AGENTS = [
    {
        "id": "main-001",
        "role": "main",
        "name": "Main Agent",
        "description": "Main Agent - Handles all user requests directly",
        "system_prompt": "You are an AI assistant that helps users with various tasks.",
        "status": "idle",
        "capabilities": '["general", "coordination", "analysis", "execution"]',
    },
]

def init_default_agents(db: Session):
    """Initialize default agents if they don't exist"""
    for agent_data in DEFAULT_AGENTS:
        existing = db.query(Agent).filter(Agent.id == agent_data["id"]).first()
        if not existing:
            agent = Agent(**agent_data)
            db.add(agent)
    db.commit()

@router.get("", response_model=List[AgentResponse])
async def get_agents(db: Session = Depends(get_db)):
    """Get all agents"""
    init_default_agents(db)
    agents = db.query(Agent).all()
    return agents

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent by ID"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str, db: Session = Depends(get_db)):
    """Get agent status"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": agent.status}

@router.post("/{agent_id}/chat")
async def send_to_agent(agent_id: str, content: str, db: Session = Depends(get_db)):
    """Send message to agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    # In a real implementation, this would process the message
    return {"message": "Message sent", "agent_id": agent_id}

@router.get("/{agent_id}/history")
async def get_agent_history(agent_id: str, db: Session = Depends(get_db)):
    """Get agent message history"""
    return []

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, updates: AgentUpdate, db: Session = Depends(get_db)):
    """Update agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    db.commit()
    db.refresh(agent)
    return agent
