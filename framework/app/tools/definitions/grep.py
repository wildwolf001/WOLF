"""
Grep Tool
Searches for text patterns in files
"""
import os
import re
from typing import Dict, Any, Optional, List


class GrepTool:
    """Tool for searching text in files"""

    def __init__(self, base_path: Optional[str] = None):
        self._base_path = base_path

    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to base"""
        if self._base_path and not os.path.isabs(path):
            return os.path.join(self._base_path, path)
        return path

    async def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_pattern: str = "*",
        case_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Search for pattern in files"""
        try:
            search_path = self._resolve_path(path) if path else self._base_path or os.getcwd()

            if not os.path.exists(search_path):
                return {
                    "success": False,
                    "error": f"Path not found: {search_path}"
                }

            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            results = []
            for dirpath, dirnames, filenames in os.walk(search_path):
                # Skip hidden directories
                dirnames[:] = [d for d in dirnames if not d.startswith('.')]

                for filename in filenames:
                    if not filename.endswith('.') and file_pattern != "*":
                        if not self._matches(file_pattern, filename):
                            continue

                    filepath = os.path.join(dirpath, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                            for line_num, line in enumerate(f, 1):
                                if regex.search(line):
                                    rel_path = os.path.relpath(filepath, search_path)
                                    results.append({
                                        "file": rel_path,
                                        "line": line_num,
                                        "content": line.rstrip()
                                    })
                    except Exception:
                        continue

            return {
                "success": True,
                "pattern": pattern,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _matches(self, pattern: str, filename: str) -> bool:
        """Check if filename matches pattern"""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        return {
            "name": "grep",
            "description": "Search for text patterns in files",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to filter (*.py, *.js, etc.)",
                        "default": "*"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search",
                        "default": False
                    }
                },
                "required": ["pattern"]
            }
        }


async def grep(
    pattern: str,
    base_path: Optional[str] = None,
    path: Optional[str] = None,
    file_pattern: str = "*",
    case_sensitive: bool = False
) -> Dict[str, Any]:
    """Search for pattern in files"""
    tool = GrepTool(base_path=base_path)
    return await tool.execute(pattern, path=path, file_pattern=file_pattern, case_sensitive=case_sensitive)