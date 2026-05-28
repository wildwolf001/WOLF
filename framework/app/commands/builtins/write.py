"""Write Command - 文件写入命令"""
from typing import Dict, Any
from ..registry import Command, CommandType

write_command = Command(
    name="write",
    description="Write content to a file",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_write_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Write content to a file. This will create a new file or overwrite an existing one."
