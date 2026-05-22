"""
ToolRegistry - 工具注册表

管理和注册所有可用工具
"""
from typing import Dict, Type, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    args: list
    execute_fn: Optional[Callable] = None
    tool_class: Optional[Type] = None


class ToolRegistry:
    """
    工具注册表

    管理所有可用工具的注册和调用
    """

    def __init__(self):
        self._tools: Dict[str, ToolInfo] = {}
        self._initialized = False
        self._init_default_tools()

    def _init_default_tools(self):
        """初始化默认工具"""
        # 这里可以注册默认工具
        # 实际工具在运行时通过tools_service提供
        self._initialized = True

    def register(self, name: str, tool_class: Type = None, description: str = "", args: list = None, execute_fn: Callable = None):
        """
        注册工具

        Args:
            name: 工具名称
            tool_class: 工具类
            description: 工具描述
            args: 工具参数列表
            execute_fn: 执行函数（替代tool_class）
        """
        self._tools[name] = ToolInfo(
            name=name,
            description=description or "",
            args=args or [],
            tool_class=tool_class,
            execute_fn=execute_fn
        )

    def get(self, name: str) -> Optional[Any]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            工具实例或None
        """
        tool_info = self._tools.get(name)
        if not tool_info:
            return None

        if tool_info.execute_fn:
            return tool_info.execute_fn

        if tool_info.tool_class:
            return tool_info.tool_class()

        return None

    def list_tools(self) -> list:
        """列出所有工具"""
        return [
            {
                "name": info.name,
                "description": info.description,
                "args": info.args
            }
            for info in self._tools.values()
        ]

    def unregister(self, name: str) -> bool:
        """取消注册工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def exists(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools