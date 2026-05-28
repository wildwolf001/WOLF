"""Session Command - 会话管理命令"""
from typing import Dict, Any
from ..registry import Command, CommandType

session_command = Command(
    name="session",
    description="Manage Claude Code sessions",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_session_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Manage Claude Code sessions. Use session list to see sessions, session resume <id> to continue a session."
