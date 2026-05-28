"""
Permission Manager
Manages tool execution permissions
"""
from typing import Set, Optional


class PermissionManager:
    """Manages permissions for tool execution"""

    def __init__(self):
        self._allowed_paths: Set[str] = {"/workspace", "/tmp"}
        self._denied_paths: Set[str] = {"/etc", "/sys", "/proc"}
        self._allow_bash: bool = True
        self._allow_network: bool = True

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed for file operations"""
        # Check denied paths first
        for denied in self._denied_paths:
            if path.startswith(denied):
                return False

        # Check allowed paths
        for allowed in self._allowed_paths:
            if path.startswith(allowed):
                return True

        return False

    def is_bash_allowed(self) -> bool:
        """Check if bash execution is allowed"""
        return self._allow_bash

    def is_network_allowed(self) -> bool:
        """Check if network access is allowed"""
        return self._allow_network

    def set_allowed_paths(self, paths: Set[str]) -> None:
        """Set allowed paths"""
        self._allowed_paths = paths

    def set_denied_paths(self, paths: Set[str]) -> None:
        """Set denied paths"""
        self._denied_paths = paths

    def allow_bash(self, allowed: bool) -> None:
        """Set bash permission"""
        self._allow_bash = allowed

    def allow_network(self, allowed: bool) -> None:
        """Set network permission"""
        self._allow_network = allowed


# Global permission manager
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get global permission manager"""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager