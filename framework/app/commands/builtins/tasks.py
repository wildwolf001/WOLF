"""Tasks Command - 任务管理命令"""
from typing import Dict, Any
from ..registry import Command, CommandType

tasks_command = Command(
    name="tasks",
    description="List and manage background tasks",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_tasks_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "List all running and completed background tasks. Use task stop <id> to stop a task."
