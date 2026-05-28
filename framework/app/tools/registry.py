"""
Tool Registry - 工具注册表
参考 cc-haha-main/src/tools.ts
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Awaitable
import asyncio

@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    input_schema: dict
    function: Callable[[dict, dict], Awaitable['ToolResult']]
    is_read_only: bool = False  # 读工具可并发
    permission: str = "read"  # read | write | shell | network | agent
    permissions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为 OpenAI 标准 function calling 格式"""
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': self.input_schema,
            }
        }

    @property
    def permission_label(self) -> str:
        """权限标签"""
        return self.permission

@dataclass
class ToolResult:
    """工具执行结果"""
    tool_call_id: str
    name: str
    result: Any
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'tool_call_id': self.tool_call_id,
            'name': self.name,
            'result': self.result,
            'success': self.success,
            'error': self.error,
        }

class ToolRegistry:
    """
    工具注册表
    管理所有可用工具
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._lock = asyncio.Lock()

    def register(self, definition: ToolDefinition) -> None:
        """注册工具"""
        self._tools[definition.name] = definition

    def get(self, name: str) -> Optional[ToolDefinition]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """列出所有工具"""
        return list(self._tools.values())

    def list_read_only_tools(self) -> List[ToolDefinition]:
        """列出只读工具"""
        return [t for t in self._tools.values() if t.is_read_only]

    def list_writable_tools(self) -> List[ToolDefinition]:
        """列出可写工具"""
        return [t for t in self._tools.values() if not t.is_read_only]

    def get_permissions(self, tool_name: str) -> List[str]:
        """获取工具权限"""
        tool = self.get(tool_name)
        return tool.permissions if tool else []

    def has(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

# 全局注册表实例
tool_registry = ToolRegistry()

# 工具名称常量
AGENT_TOOL_NAME = "Agent"
BASH_TOOL_NAME = "Bash"
READ_TOOL_NAME = "Read"
EDIT_TOOL_NAME = "Edit"
WRITE_TOOL_NAME = "Write"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"
WEB_SEARCH_TOOL_NAME = "WebSearch"
WEB_FETCH_TOOL_NAME = "WebFetch"
TASK_CREATE_TOOL_NAME = "TaskCreate"
TASK_STOP_TOOL_NAME = "TaskStop"
