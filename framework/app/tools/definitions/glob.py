"""
Glob Tool
Finds files matching patterns
"""
import os
import fnmatch
from typing import List, Dict, Any, Optional


class GlobTool:
    """Tool for finding files by pattern"""

    def __init__(self, base_path: Optional[str] = None):
        self._base_path = base_path

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to base"""
        if self._base_path and not os.path.isabs(path):
            return os.path.join(self._base_path, path)
        return path

    async def execute(self, pattern: str, root: Optional[str] = None) -> Dict[str, Any]:
        """Find files matching a pattern"""
        try:
            search_root = self._resolve_path(root) if root else self._base_path or os.getcwd()

            if not os.path.exists(search_root):
                return {
                    "success": False,
                    "error": f"Directory not found: {search_root}"
                }

            matches = []
            for dirpath, dirnames, filenames in os.walk(search_root):
                # Skip hidden directories
                dirnames[:] = [d for d in dirnames if not d.startswith('.')]

                for filename in filenames:
                    if fnmatch.fnmatch(filename, pattern):
                        full_path = os.path.join(dirpath, filename)
                        rel_path = os.path.relpath(full_path, search_root)
                        matches.append(rel_path)

            return {
                "success": True,
                "pattern": pattern,
                "matches": matches,
                "count": len(matches)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        return {
            "name": "glob",
            "description": "Find files matching a pattern",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match (e.g., *.py)"
                    },
                    "root": {
                        "type": "string",
                        "description": "Root directory to search from"
                    }
                },
                "required": ["pattern"]
            }
        }


async def glob_files(
    pattern: str,
    base_path: Optional[str] = None,
    root: Optional[str] = None
) -> Dict[str, Any]:
    """Find files matching a pattern"""
    tool = GlobTool(base_path=base_path)
    return await tool.execute(pattern, root=root)