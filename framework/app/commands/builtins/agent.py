"""Agent Command - Agent管理命令"""
from typing import Dict, Any
from ..registry import Command, CommandType

agent_command = Command(
    name="agent",
    description="Spawn an agent to complete a task",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_agent_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Spawn a sub-agent to help complete complex tasks. The agent will work independently and report back."
