"""
File Write Tool
Writes content to files
"""
import os
from typing import Dict, Any, Optional


class FileWriteTool:
    """Tool for writing files"""

    def __init__(self, base_path: Optional[str] = None):
        self._base_path = base_path

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to base"""
        if self._base_path and not os.path.isabs(path):
            return os.path.join(self._base_path, path)
        return path

    async def execute(self, path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
        """Write content to a file"""
        try:
            full_path = self._resolve_path(path)

            # Create directory if needed
            if create_dirs:
                dir_path = os.path.dirname(full_path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                "success": True,
                "path": path,
                "bytes_written": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path
            }

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        return {
            "name": "write",
            "description": "Write content to a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "description": "Create parent directories if they don't exist",
                        "default": True
                    }
                },
                "required": ["path", "content"]
            }
        }


async def write_file(
    path: str,
    content: str,
    base_path: Optional[str] = None,
    create_dirs: bool = True
) -> Dict[str, Any]:
    """Write content to a file"""
    tool = FileWriteTool(base_path=base_path)
    return await tool.execute(path, content, create_dirs=create_dirs)