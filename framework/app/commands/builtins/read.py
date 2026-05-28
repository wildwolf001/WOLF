"""Read Command - 文件读取命令"""
from typing import Dict, Any
from ..registry import Command, CommandType

read_command = Command(
    name="read",
    description="Read file contents",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_read_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Read the contents of a file. Provide the file path to read."
