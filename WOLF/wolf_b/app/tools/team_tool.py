"""
Team Tools - Create and manage AI teams
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

router = APIRouter()

# Team storage
teams_db: Dict[str, dict] = {}


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    members: List[str] = []  # Agent IDs
    roles: Dict[str, str] = {}  # agent_id -> role


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class Team(BaseModel):
    id: str
    name: str
    description: str
    members: List[str]
    roles: Dict[str, str]
    status: str  # active, paused, completed
    created_at: str


class TaskAssignment(BaseModel):
    task_id: str
    agent_id: str
    priority: int = 0


@router.post("/teams")
async def create_team(input: TeamCreate) -> Team:
    """Create a new team"""
    team_id = f"team-{uuid.uuid4().hex[:8]}"

    team = {
        "id": team_id,
        "name": input.name,
        "description": input.description,
        "members": input.members,
        "roles": input.roles,
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }

    teams_db[team_id] = team
    return team


@router.get("/teams")
async def list_teams(status: Optional[str] = None) -> List[Team]:
    """List all teams"""
    teams = list(teams_db.values())

    if status:
        teams = [t for t in teams if t["status"] == status]

    return teams


@router.get("/teams/{team_id}")
async def get_team(team_id: str) -> Team:
    """Get team by ID"""
    if team_id not in teams_db:
        raise HTTPException(status_code=404, detail="Team not found")
    return teams_db[team_id]


@router.put("/teams/{team_id}")
async def update_team(team_id: str, updates: TeamUpdate) -> Team:
    """Update a team"""
    if team_id not in teams_db:
        raise HTTPException(status_code=404, detail="Team not found")

    team = teams_db[team_id]
    update_data = updates.model_dump(exclude_none=True)

    for key, value in update_data.items():
        team[key] = value

    return team


@router.delete("/teams/{team_id}")
async def delete_team(team_id: str) -> dict:
    """Delete a team"""
    if team_id not in teams_db:
        raise HTTPException(status_code=404, detail="Team not found")

    del teams_db[team_id]
    return {"success": True, "message": "Team deleted"}


@router.post("/teams/{team_id}/members")
async def add_team_member(team_id: str, agent_id: str, role: str = "member") -> dict:
    """Add a member to a team"""
    if team_id not in teams_db:
        raise HTTPException(status_code=404, detail="Team not found")

    team = teams_db[team_id]
    if agent_id not in team["members"]:
        team["members"].append(agent_id)
        team["roles"][agent_id] = role

    return {"success": True, "members": team["members"]}


@router.delete("/teams/{team_id}/members/{agent_id}")
async def remove_team_member(team_id: str, agent_id: str) -> dict:
    """Remove a member from a team"""
    if team_id not in teams_db:
        raise HTTPException(status_code=404, detail="Team not found")

    team = teams_db[team_id]
    if agent_id in team["members"]:
        team["members"].remove(agent_id)
        if agent_id in team["roles"]:
            del team["roles"][agent_id]

    return {"success": True, "members": team["members"]}


@router.post("/teams/{team_id}/tasks")
async def assign_task_to_team(team_id: str, assignment: TaskAssignment) -> dict:
    """Assign a task to a team member"""
    if team_id not in teams_db:
        raise HTTPException(status_code=404, detail="Team not found")

    team = teams_db[team_id]
    if assignment.agent_id not in team["members"]:
        raise HTTPException(status_code=400, detail="Agent not a team member")

    # Store assignment
    task_key = f"team_tasks_{team_id}"
    if task_key not in teams_db:
        teams_db[task_key] = []

    teams_db[task_key].append({
        "task_id": assignment.task_id,
        "agent_id": assignment.agent_id,
        "priority": assignment.priority,
        "assigned_at": datetime.now().isoformat()
    })

    return {"success": True, "task_assigned": assignment.task_id}


@router.get("/teams/{team_id}/tasks")
async def get_team_tasks(team_id: str) -> List[dict]:
    """Get all tasks assigned to a team"""
    task_key = f"team_tasks_{team_id}"
    return teams_db.get(task_key, [])