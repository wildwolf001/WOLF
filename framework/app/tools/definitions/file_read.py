"""
File Read Tool
Reads file contents
"""
import os
from typing import Dict, Any, Optional


class FileReadTool:
    """Tool for reading files"""

    def __init__(self, base_path: Optional[str] = None):
        self._base_path = base_path

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to base"""
        if self._base_path and not os.path.isabs(path):
            return os.path.join(self._base_path, path)
        return path

    async def execute(self, path: str = None, file_path: str = None, offset: int = 0, limit: Optional[int] = None) -> Dict[str, Any]:
        """Read a file"""
        # Support both 'path' and 'file_path' parameter names
        actual_path = path or file_path
        if not actual_path:
            return {
                "success": False,
                "error": "Missing required parameter: path or file_path"
            }

        try:
            full_path = self._resolve_path(actual_path)

            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": f"File not found: {actual_path}"
                }

            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                if offset > 0:
                    f.seek(offset)

                if limit:
                    content = f.read(limit)
                else:
                    content = f.read()

            return {
                "success": True,
                "path": actual_path,
                "content": content,
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": actual_path
            }

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        return {
            "name": "read",
            "description": "Read the contents of a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Byte offset to start reading from",
                        "default": 0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum bytes to read"
                    }
                },
                "required": ["path"]
            }
        }


async def read_file(
    path: str,
    base_path: Optional[str] = None,
    offset: int = 0,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """Read a file"""
    tool = FileReadTool(base_path=base_path)
    return await tool.execute(path, offset=offset, limit=limit)