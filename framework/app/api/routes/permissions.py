"""
Permissions Route
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

router = APIRouter()

# Permission modes
_permission_modes = [
    {"id": "read_only", "name": "Read Only", "icon": "📖", "level": 1, "description": "Can only read files, no write operations"},
    {"id": "standard", "name": "Standard", "icon": "✏️", "level": 2, "description": "Can read and write files, limited destructive operations"},
    {"id": "admin", "name": "Administrator", "icon": "🔧", "level": 3, "description": "Full access including destructive operations"}
]
_current_permission_mode = "standard"


@router.get("/permissions/modes")
async def get_permission_modes() -> dict:
    """Get available permission modes"""
    return {"modes": _permission_modes}


@router.get("/permissions/current")
async def get_current_permission() -> dict:
    """Get current permission mode"""
    current = next((m for m in _permission_modes if m["id"] == _current_permission_mode), None)
    return {"current_mode": current}


@router.post("/permissions/switch")
async def switch_permission_mode(request: dict) -> dict:
    """Switch permission mode"""
    mode_id = request.get("mode_id")

    if not mode_id:
        raise HTTPException(status_code=400, detail="mode_id is required")

    mode = next((m for m in _permission_modes if m["id"] == mode_id), None)
    if not mode:
        raise HTTPException(status_code=404, detail=f"Permission mode not found: {mode_id}")

    global _current_permission_mode
    _current_permission_mode = mode_id

    return {"success": True, "mode": mode}