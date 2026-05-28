"""
Harness Module
File harness for workspace operations
"""
import os
from typing import Dict, Any, Optional


class FileHarness:
    """Harness for file operations within workspace"""

    def __init__(self, workspace_path: str):
        self._workspace_path = workspace_path
        os.makedirs(workspace_path, exist_ok=True)

    def _resolve_path(self, path: str) -> str:
        """Resolve path within workspace"""
        if os.path.isabs(path):
            # Security: ensure absolute paths are within workspace
            if not path.startswith(self._workspace_path):
                raise ValueError(f"Path outside workspace: {path}")
            return path
        return os.path.join(self._workspace_path, path)

    async def read(self, path: str) -> str:
        """Read a file"""
        full_path = self._resolve_path(path)
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    async def write(self, path: str, content: str) -> None:
        """Write a file"""
        full_path = self._resolve_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

    async def exists(self, path: str) -> bool:
        """Check if file exists"""
        full_path = self._resolve_path(path)
        return os.path.exists(full_path)

    async def list_dir(self, path: str = "") -> list[str]:
        """List directory contents"""
        full_path = self._resolve_path(path)
        if not os.path.isdir(full_path):
            return []
        return os.listdir(full_path)