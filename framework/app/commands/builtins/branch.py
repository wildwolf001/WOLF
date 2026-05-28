"""Git Branch Command"""
from typing import Dict, Any
from ..registry import Command, CommandType

branch_command = Command(
    name="branch",
    description="List, create, or delete branches",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_branch_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Manage git branches. Use git branch, git checkout, or git switch commands."
