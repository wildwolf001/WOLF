"""History Command - 历史记录命令"""
from typing import Dict, Any
from ..registry import Command, CommandType

history_command = Command(
    name="history",
    description="Show conversation history",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_history_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Show the conversation history for the current session."
