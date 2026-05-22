"""
Permission System - Role-based access control
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

router = APIRouter()

# Permission modes
PERMISSION_MODES = {
    "read_only": {
        "id": "read_only",
        "name": "Read Only",
        "description": "Can view data but cannot make changes",
        "level": 0,
        "capabilities": [
            "view_dashboard",
            "view_results",
            "view_documents",
            "view_knowledge",
            "view_files",
        ],
        "icon": "👁️",
    },
    "user": {
        "id": "user",
        "name": "User",
        "description": "Standard user with ability to create and modify",
        "level": 1,
        "capabilities": [
            "view_dashboard",
            "view_results",
            "view_documents",
            "view_knowledge",
            "view_files",
            "create_tasks",
            "create_sessions",
            "create_memories",
            "use_chat",
            "create_teams",
        ],
        "icon": "👤",
    },
    "developer": {
        "id": "developer",
        "name": "Developer",
        "description": "Can modify code and configuration",
        "level": 2,
        "capabilities": [
            "view_dashboard",
            "view_results",
            "view_documents",
            "view_knowledge",
            "view_files",
            "create_tasks",
            "create_sessions",
            "create_memories",
            "use_chat",
            "create_teams",
            "edit_config",
            "manage_agents",
            "run_tests",
        ],
        "icon": "💻",
    },
    "admin": {
        "id": "admin",
        "name": "Admin",
        "description": "Full access to all features and settings",
        "level": 3,
        "capabilities": [
            "view_dashboard",
            "view_results",
            "view_documents",
            "view_knowledge",
            "view_files",
            "create_tasks",
            "create_sessions",
            "create_memories",
            "use_chat",
            "create_teams",
            "edit_config",
            "manage_agents",
            "run_tests",
            "manage_users",
            "manage_permissions",
            "delete_data",
            "system_settings",
        ],
        "icon": "🔐",
    },
}


class UserProfile(BaseModel):
    user_id: str
    name: str
    mode: str = "user"
    capabilities: List[str] = []
    restrictions: List[str] = []
    last_active: Optional[str] = None


class PermissionCheck(BaseModel):
    capability: str
    user_id: Optional[str] = None


# Current user state (in production, this would be in a database)
_current_mode = "user"
_current_user = {
    "user_id": "local-user",
    "name": "Local User",
    "mode": "user",
    "capabilities": PERMISSION_MODES["user"]["capabilities"],
}


@router.get("/modes")
async def list_permission_modes():
    """List all available permission modes"""
    modes = []
    for mode_id, mode in PERMISSION_MODES.items():
        modes.append({
            "id": mode_id,
            "name": mode["name"],
            "description": mode["description"],
            "level": mode["level"],
            "capabilities": mode["capabilities"],
            "icon": mode["icon"],
        })
    return {"success": True, "modes": modes}


@router.get("/modes/{mode_id}")
async def get_permission_mode(mode_id: str):
    """Get details of a specific permission mode"""
    if mode_id not in PERMISSION_MODES:
        raise HTTPException(status_code=404, detail="Permission mode not found")
    mode = PERMISSION_MODES[mode_id]
    return {
        "success": True,
        "mode": {
            "id": mode_id,
            "name": mode["name"],
            "description": mode["description"],
            "level": mode["level"],
            "capabilities": mode["capabilities"],
            "icon": mode["icon"],
        }
    }


@router.get("/current")
async def get_current_permissions():
    """Get current user's permission mode and capabilities"""
    global _current_mode, _current_user
    mode = PERMISSION_MODES.get(_current_mode, PERMISSION_MODES["user"])
    return {
        "success": True,
        "current_mode": {
            "id": _current_mode,
            "name": mode["name"],
            "description": mode["description"],
            "level": mode["level"],
            "icon": mode["icon"],
        },
        "user": _current_user,
        "capabilities": mode["capabilities"],
    }


@router.post("/switch")
async def switch_permission_mode(mode_id: str):
    """Switch to a different permission mode"""
    global _current_mode, _current_user
    if mode_id not in PERMISSION_MODES:
        raise HTTPException(status_code=404, detail="Permission mode not found")

    _current_mode = mode_id
    mode = PERMISSION_MODES[mode_id]
    _current_user["mode"] = mode_id
    _current_user["capabilities"] = mode["capabilities"]

    return {
        "success": True,
        "message": f"Switched to {mode['name']} mode",
        "mode": {
            "id": mode_id,
            "name": mode["name"],
            "icon": mode["icon"],
        },
        "capabilities": mode["capabilities"],
    }


@router.post("/check")
async def check_permission(check: PermissionCheck):
    """Check if current user has a specific capability"""
    global _current_mode
    mode = PERMISSION_MODES.get(_current_mode, PERMISSION_MODES["user"])

    has_capability = check.capability in mode["capabilities"]

    return {
        "success": True,
        "capability": check.capability,
        "allowed": has_capability,
        "current_mode": _current_mode,
        "required_level": mode["level"],
    }


@router.get("/capabilities")
async def list_capabilities():
    """List all available capabilities across all modes"""
    all_caps = set()
    for mode in PERMISSION_MODES.values():
        all_caps.update(mode["capabilities"])

    return {
        "success": True,
        "capabilities": sorted(list(all_caps)),
        "by_mode": {
            mode_id: mode["capabilities"]
            for mode_id, mode in PERMISSION_MODES.items()
        },
    }


@router.post("/validate-action")
async def validate_action(action: dict):
    """
    Validate if an action is permitted under current permissions.
    Used by frontend to disable UI elements based on permissions.
    """
    global _current_mode
    mode = PERMISSION_MODES.get(_current_mode, PERMISSION_MODES["user"])

    action_type = action.get("type", "")
    target = action.get("target", "")

    # Map actions to required capabilities
    action_capability_map = {
        "create_task": "create_tasks",
        "create_session": "create_sessions",
        "delete_session": "delete_data",
        "create_memory": "create_memories",
        "delete_memory": "delete_data",
        "create_team": "create_teams",
        "delete_team": "delete_data",
        "edit_config": "edit_config",
        "manage_agents": "manage_agents",
        "use_chat": "use_chat",
        "view_dashboard": "view_dashboard",
        "view_results": "view_results",
        "view_settings": "system_settings",
        "delete_data": "delete_data",
    }

    required_capability = action_capability_map.get(action_type)

    if not required_capability:
        # Unknown action type - allow by default for safety
        return {
            "success": True,
            "allowed": True,
            "reason": "Unknown action type",
        }

    allowed = required_capability in mode["capabilities"]

    return {
        "success": True,
        "action_type": action_type,
        "target": target,
        "allowed": allowed,
        "required_capability": required_capability,
        "current_mode": _current_mode,
        "reason": mode["name"] if allowed else f"Requires {required_capability} capability",
    }


# Initialize default mode
_current_mode = "user"
_current_user = {
    "user_id": "local-user",
    "name": "Local User",
    "mode": "user",
    "capabilities": PERMISSION_MODES["user"]["capabilities"],
    "last_active": datetime.now().isoformat(),
}


def get_current_permission_mode() -> str:
    """Get the current permission mode ID"""
    return _current_mode


def get_current_permission_level() -> int:
    """Get the current permission level"""
    mode = PERMISSION_MODES.get(_current_mode, PERMISSION_MODES["user"])
    return mode.get("level", 1)


def can_perform_file_operation(operation: str) -> tuple[bool, str]:
    """
    Check if the current permission mode allows a file operation.

    Args:
        operation: One of "read", "write", "edit", "delete", "execute"

    Returns:
        (allowed, reason) - whether the operation is allowed and why
    """
    mode = PERMISSION_MODES.get(_current_mode, PERMISSION_MODES["user"])
    level = mode.get("level", 1)

    # All modes can read
    read_operations = {"read", "list", "glob", "grep", "search"}
    if operation.lower() in read_operations:
        return True, "Allowed"

    # Write operations require level >= 1 (user mode)
    write_operations = {"write", "edit", "create"}
    if operation.lower() in write_operations:
        if level < 1:
            return False, f"Operation '{operation}' requires at least 'user' permission mode"
        return True, "Allowed"

    # Delete operations require level >= 2 (developer mode)
    delete_operations = {"delete", "remove"}
    if operation.lower() in delete_operations:
        if level < 2:
            return False, f"Operation '{operation}' requires at least 'developer' permission mode"
        return True, "Allowed"

    # Execute operations require level >= 2 (developer mode)
    execute_operations = {"execute", "bash", "run"}
    if operation.lower() in execute_operations:
        if level < 2:
            return False, f"Operation '{operation}' requires at least 'developer' permission mode"
        return True, "Allowed"

    # Unknown operation - allow by default for safety
    return True, "Allowed"


# =============================================================================
# 交互式权限 API - 参考 Claude Code 的权限系统
# =============================================================================

class PermissionModeRequest(BaseModel):
    mode: str  # "default", "plan", "acceptEdits", "bypassPermissions", "dontAsk"


class PermissionResponseRequest(BaseModel):
    request_id: str
    action: str  # "allow", "deny", "allow_always", "deny_always"
    feedback: Optional[str] = None


@router.get("/interactive/mode")
async def get_permission_mode():
    """获取当前交互式权限模式"""
    from app.services.permission_service import get_interactive_permission_service
    service = get_interactive_permission_service()
    mode = service.get_mode()
    return {
        "success": True,
        "mode": mode.value,
        "is_interactive": mode.is_interactive(),
        "allows_execution": mode.allows_execution()
    }


@router.post("/interactive/mode")
async def set_permission_mode(request: PermissionModeRequest):
    """设置交互式权限模式"""
    from app.core.permission_mode import PermissionMode
    from app.services.permission_service import get_interactive_permission_service

    try:
        mode = PermissionMode.from_string(request.mode)
        service = get_interactive_permission_service()
        old_mode = service.get_mode()
        service.set_mode(mode)

        return {
            "success": True,
            "old_mode": old_mode.value,
            "new_mode": mode.value,
            "message": f"Permission mode changed from {old_mode.value} to {mode.value}"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid permission mode: {request.mode}")


@router.get("/interactive/pending")
async def get_pending_permission_requests():
    """获取所有待处理的权限请求"""
    from app.services.permission_service import get_interactive_permission_service
    service = get_interactive_permission_service()
    requests = service.get_pending_requests()

    return {
        "success": True,
        "pending_requests": [r.to_dict() for r in requests],
        "count": len(requests)
    }


@router.post("/interactive/respond")
async def respond_to_permission_request(request: PermissionResponseRequest):
    """
    用户对权限请求做出响应

    前端调用此 API 来通知后端用户的选择
    """
    from app.services.permission_service import get_interactive_permission_service
    from app.models.permission import PermissionResponse

    service = get_interactive_permission_service()

    # 创建响应对象
    response = PermissionResponse(
        request_id=request.request_id,
        action=request.action,
        feedback=request.feedback
    )

    # 查找对应的等待中的请求并设置结果
    # 注意：实际的响应处理通过 WebSocket 的 wait_for_permission_response 完成
    # 这里主要是用于日志记录和状态同步

    return {
        "success": True,
        "request_id": request.request_id,
        "action": request.action,
        "message": f"Response recorded: {request.action}"
    }


@router.get("/interactive/rules")
async def get_permission_rules():
    """获取当前会话的权限规则"""
    from app.services.permission_service import get_interactive_permission_service
    service = get_interactive_permission_service()

    return {
        "success": True,
        "always_allowed": [
            {"tool_name": r.tool_name, "pattern": r.pattern}
            for r in service.always_allowed_rules
        ],
        "always_denied": [
            {"tool_name": r.tool_name, "pattern": r.pattern}
            for r in service.always_denied_rules
        ]
    }


@router.post("/interactive/rules/clear")
async def clear_permission_rules():
    """清除所有会话权限规则"""
    from app.services.permission_service import get_interactive_permission_service
    service = get_interactive_permission_service()
    service.clear_rules()

    return {
        "success": True,
        "message": "All session permission rules cleared"
    }