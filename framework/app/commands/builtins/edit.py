"""Edit Command - 文件编辑命令"""
from typing import Dict, Any
from ..registry import Command, CommandType

edit_command = Command(
    name="edit",
    description="Edit file contents",
    command_type=CommandType.SLASH,
    source="builtin",
)

async def get_edit_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    return "Edit a file by replacing specific text. Provide the file path, old text, and new text."
