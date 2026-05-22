"""
Skills API - Plugin-based skill system
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

router = APIRouter()

# Skills storage
_skills: Dict[str, dict] = {}
_skill_definitions: Dict[str, dict] = {}  # Full skill definitions with content


class SkillCreate(BaseModel):
    name: str
    description: str
    category: str = "general"
    risk: str = "safe"  # safe, warning, danger
    content: str = ""  # Markdown content
    source: str = "custom"  # builtin, custom, community
    triggers: List[str] = []  # Keywords that trigger this skill
    examples: List[str] = []


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    risk: Optional[str] = None
    content: Optional[str] = None
    enabled: Optional[bool] = None
    triggers: Optional[List[str]] = None
    examples: Optional[List[str]] = None


class Skill(BaseModel):
    id: str
    name: str
    description: str
    category: str
    risk: str
    source: str
    enabled: bool
    created_at: str
    updated_at: str
    triggers: List[str]
    examples: List[str]


# Default skills (builtins)
DEFAULT_SKILLS = [
    {
        "id": "skill-bug-hunter",
        "name": "Bug Hunter",
        "description": "Systematically finds and fixes bugs using proven debugging techniques",
        "category": "development",
        "risk": "safe",
        "source": "builtin",
        "enabled": True,
        "triggers": ["bug", "fix", "debug", "error", "crash", "issue"],
        "examples": ["Find and fix the login bug", "Debug why the form fails"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "skill-code-review",
        "name": "Code Review",
        "description": "Review code for quality, security, and best practices",
        "category": "development",
        "risk": "safe",
        "source": "builtin",
        "enabled": True,
        "triggers": ["review", "pr", "pull request", "check code"],
        "examples": ["Review this PR", "Check code quality"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "skill-research",
        "name": "Research",
        "description": "Conduct deep research on topics with literature review",
        "category": "research",
        "risk": "safe",
        "source": "builtin",
        "enabled": True,
        "triggers": ["research", "investigate", "study", "analyze"],
        "examples": ["Research this topic", "Investigate best practices"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "skill-write",
        "name": "Technical Writing",
        "description": "Create clear technical documentation and reports",
        "category": "writing",
        "risk": "safe",
        "source": "builtin",
        "enabled": True,
        "triggers": ["write", "document", "report", "draft"],
        "examples": ["Write documentation", "Create a report"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "skill-refactor",
        "name": "Refactor",
        "description": "Improve code structure without changing behavior",
        "category": "development",
        "risk": "warning",
        "source": "builtin",
        "enabled": True,
        "triggers": ["refactor", "improve", "clean up", "restructure"],
        "examples": ["Refactor this module", "Clean up the codebase"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
]


def init_default_skills():
    """Initialize default skills"""
    for skill in DEFAULT_SKILLS:
        if skill["id"] not in _skills:
            _skills[skill["id"]] = skill


@router.post("")
async def create_skill(skill: SkillCreate):
    """Create a new skill"""
    skill_id = f"skill-{uuid.uuid4().hex[:8]}"

    new_skill = {
        "id": skill_id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "risk": skill.risk,
        "source": skill.source,
        "enabled": True,
        "triggers": skill.triggers,
        "examples": skill.examples,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    _skills[skill_id] = new_skill
    if skill.content:
        _skill_definitions[skill_id] = {"content": skill.content}

    return {"success": True, "skill": new_skill}


@router.get("")
async def list_skills(category: Optional[str] = None, enabled: Optional[bool] = None):
    """List all skills with optional filtering"""
    skills = list(_skills.values())

    if category:
        skills = [s for s in skills if s.get("category") == category]
    if enabled is not None:
        skills = [s for s in skills if s.get("enabled") == enabled]

    return {"success": True, "skills": skills}


@router.get("/categories")
async def list_categories():
    """List all skill categories"""
    categories = set(s.get("category") for s in _skills.values())
    return {"success": True, "categories": list(categories)}


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """Get skill details with full content"""
    if skill_id not in _skills:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills[skill_id].copy()
    if skill_id in _skill_definitions:
        skill["content"] = _skill_definitions[skill_id].get("content", "")

    return {"success": True, "skill": skill}


@router.put("/{skill_id}")
async def update_skill(skill_id: str, updates: SkillUpdate):
    """Update a skill"""
    if skill_id not in _skills:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills[skill_id]
    update_data = updates.model_dump(exclude_none=True)

    for key, value in update_data.items():
        if key != "id" and key != "created_at":
            skill[key] = value
    skill["updated_at"] = datetime.now().isoformat()

    return {"success": True, "skill": skill}


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    """Delete a skill (only custom skills)"""
    if skill_id not in _skills:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills[skill_id]
    if skill.get("source") == "builtin":
        raise HTTPException(status_code=400, detail="Cannot delete builtin skills")

    del _skills[skill_id]
    if skill_id in _skill_definitions:
        del _skill_definitions[skill_id]

    return {"success": True, "message": "Skill deleted"}


@router.post("/{skill_id}/toggle")
async def toggle_skill(skill_id: str):
    """Enable or disable a skill"""
    if skill_id not in _skills:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills[skill_id]
    skill["enabled"] = not skill["enabled"]
    skill["updated_at"] = datetime.now().isoformat()

    return {"success": True, "skill": skill}


@router.post("/{skill_id}/content")
async def update_skill_content(skill_id: str, content: str):
    """Update skill markdown content"""
    if skill_id not in _skills:
        raise HTTPException(status_code=404, detail="Skill not found")

    _skill_definitions[skill_id] = {"content": content}
    _skills[skill_id]["updated_at"] = datetime.now().isoformat()

    return {"success": True, "message": "Content updated"}


@router.post("/match")
async def match_skill(query: str):
    """Find skills that match a query based on triggers"""
    query_lower = query.lower()
    matched_skills = []

    for skill in _skills.values():
        if not skill.get("enabled", True):
            continue

        # Check triggers
        for trigger in skill.get("triggers", []):
            if trigger.lower() in query_lower:
                matched_skills.append({
                    "skill": skill,
                    "matched_on": f"trigger: {trigger}"
                })
                break

        # Check name/description
        if not any(m["skill"]["id"] == skill["id"] for m in matched_skills):
            if (query_lower in skill["name"].lower() or
                query_lower in skill["description"].lower()):
                matched_skills.append({
                    "skill": skill,
                    "matched_on": "name/description"
                })

    return {
        "success": True,
        "matches": matched_skills,
        "query": query
    }


# Initialize default skills
init_default_skills()