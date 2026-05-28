"""
File Edit Tool
Edits specific parts of a file
"""
import os
import re
from typing import Dict, Any, Optional


class FileEditTool:
    """Tool for editing files"""

    def __init__(self, base_path: Optional[str] = None):
        self._base_path = base_path

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to base"""
        if self._base_path and not os.path.isabs(path):
            return os.path.join(self._base_path, path)
        return path

    async def execute(
        self,
        path: str,
        old_text: str,
        new_text: str,
        all_instances: bool = False
    ) -> Dict[str, Any]:
        """Edit a file by replacing text"""
        try:
            full_path = self._resolve_path(path)

            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }

            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            if all_instances:
                new_content, count = re.subn(re.escape(old_text), new_text, content)
            else:
                if old_text in content:
                    new_content = content.replace(old_text, new_text, 1)
                    count = 1
                else:
                    return {
                        "success": False,
                        "error": f"Text not found: {old_text[:50]}...",
                        "path": path
                    }

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return {
                "success": True,
                "path": path,
                "replacements": count
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
            "name": "edit",
            "description": "Edit a specific part of a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit"
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Text to replace"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text"
                    },
                    "all_instances": {
                        "type": "boolean",
                        "description": "Replace all instances",
                        "default": False
                    }
                },
                "required": ["path", "old_text", "new_text"]
            }
        }


async def edit_file(
    path: str,
    old_text: str,
    new_text: str,
    base_path: Optional[str] = None,
    all_instances: bool = False
) -> Dict[str, Any]:
    """Edit a file"""
    tool = FileEditTool(base_path=base_path)
    return await tool.execute(path, old_text, new_text, all_instances=all_instances)