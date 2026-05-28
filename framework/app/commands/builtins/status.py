"""Git Status Command"""
from typing import Dict, Any
from ..registry import Command, CommandType

status_command = Command(
    name="status",
    description="Show the working tree status",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_status_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Show the current git status - which files are modified, staged, or untracked."
