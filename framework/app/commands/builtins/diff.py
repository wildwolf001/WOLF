"""Git Diff Command"""
from typing import Dict, Any
from ..registry import Command, CommandType

diff_command = Command(
    name="diff",
    description="Show changes between commits, commit and working tree, etc.",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_diff_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Show the differences between the current state and the last commit."
