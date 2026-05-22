"""
Teams API - Agent team management and communication

================================================================================
DEPRECATED - Multi-agent teams have been disabled
================================================================================

This API is deprecated. Multi-agent collaboration has been replaced with
single-agent direct execution mode.

Changes:
- OLD: MainAgent → SharedWorkspace → MultiAgents → Collaboration
- NEW: MainAgent.think() → LLM Loop → Tools → Direct Response

All team operations now return 410 Gone status.

================================================================================
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# Hard disable teams functionality
TEAMS_ENABLED = False

router = APIRouter()


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    agents: List[str] = []


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agents: Optional[List[str]] = None


class MessageCreate(BaseModel):
    content: str
    msg_type: str = "message"


class TeamMessage(BaseModel):
    id: str
    from_role: str
    to_role: str
    team_id: str
    content: str
    msg_type: str
    timestamp: datetime
    task_id: Optional[str] = None


def teams_disabled():
    """Helper to check if teams are disabled"""
    if not TEAMS_ENABLED:
        raise HTTPException(
            status_code=410,
            detail="Multi-agent teams have been disabled. Use single-agent direct execution mode instead."
        )


@router.post("/teams")
async def create_team(team: TeamCreate):
    """Create a new agent team - DEPRECATED"""
    teams_disabled()


@router.get("/teams")
async def list_teams():
    """List all teams - DEPRECATED"""
    teams_disabled()


@router.get("/teams/{team_id}")
async def get_team(team_id: str):
    """Get team by ID - DEPRECATED"""
    teams_disabled()


@router.put("/teams/{team_id}")
async def update_team(team_id: str, updates: TeamUpdate):
    """Update team - DEPRECATED"""
    teams_disabled()


@router.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """Delete team - DEPRECATED"""
    teams_disabled()


@router.post("/teams/{team_id}/agents/{agent_role}")
async def add_agent_to_team(team_id: str, agent_role: str):
    """Add an agent to a team - DEPRECATED"""
    teams_disabled()


@router.delete("/teams/{team_id}/agents/{agent_role}")
async def remove_agent_from_team(team_id: str, agent_role: str):
    """Remove an agent from a team - DEPRECATED"""
    teams_disabled()


@router.post("/teams/{team_id}/messages")
async def send_team_message(team_id: str, message: MessageCreate, from_role: str = "system"):
    """Send a message to the team - DEPRECATED"""
    teams_disabled()


@router.get("/teams/{team_id}/messages")
async def get_team_messages(team_id: str, limit: int = 50):
    """Get messages for a team - DEPRECATED"""
    teams_disabled()


@router.post("/teams/{team_id}/task")
async def assign_task_to_team(
    team_id: str,
    task: dict,
    to_role: Optional[str] = None
):
    """Assign a task to a team - DEPRECATED"""
    teams_disabled()


# Predefined teams - kept for reference, never initialized when TEAMS_ENABLED=False
DEFAULT_TEAMS = {
    "research-team": {
        "id": "research-team",
        "name": "Research Team",
        "description": "Literature review and research agents",
        "agents": ["pm", "research", "data", "writer"],
    },
    "ml-team": {
        "id": "ml-team",
        "name": "ML Team",
        "description": "Machine learning development team",
        "agents": ["pm", "ml", "developer", "data"],
    },
    "full-stack": {
        "id": "full-stack",
        "name": "Full Stack Team",
        "description": "End-to-end development team",
        "agents": ["pm", "developer", "data", "devops"],
    },
}