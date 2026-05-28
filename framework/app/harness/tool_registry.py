"""
Tool Registry
Registry for available tools
"""
from typing import Dict, Any, List, Optional, Callable


class ToolRegistry:
    """Registry for available tools"""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, handler: Callable) -> None:
        """Register a tool"""
        self._tools[name] = handler

    def get(self, name: str) -> Optional[Callable]:
        """Get a tool handler"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tools"""
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all tools"""
        schemas = []
        for name, handler in self._tools.items():
            if hasattr(handler, 'get_schema'):
                schemas.append(handler.get_schema())
            else:
                schemas.append({
                    "name": name,
                    "description": "Tool"
                })
        return schemas


# Global tool registry
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry