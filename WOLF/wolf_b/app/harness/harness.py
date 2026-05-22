"""
Harness System - 执行环境管理器

负责:
1. 文件系统操作代理
2. 进程和权限管理
3. 记忆目录保证
4. 工具执行环境管理
"""
from app.harness.file_harness import FileSystemHarness
from app.harness.tool_registry import ToolRegistry
from app.harness.permission_manager import PermissionManager
import os


class Harness:
    """
    WOLF的执行环境管理器

    核心功能：
    1. 文件系统操作（安全封装）
    2. 工具注册和执行
    3. 权限管理
    4. 记忆目录保证
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.fs = FileSystemHarness()
        self.tools = ToolRegistry()
        self.permissions = PermissionManager()
        self._initialized = True

    def ensure_memory_dir_exists(self, memory_dir: str = None):
        """保证记忆目录存在（harness核心功能）"""
        if memory_dir is None:
            memory_dir = os.path.join(os.getcwd(), "wolf_data", "memory")

        self.fs.ensure_dirs_exist([memory_dir])

        # 创建必要的子目录
        subdirs = ["sessions", "user", "project", "feedback", "reference"]
        for subdir in subdirs:
            self.fs.ensure_dirs_exist([os.path.join(memory_dir, subdir)])

        return memory_dir

    def can_execute_tool(self, tool_name: str, args: dict = None) -> bool:
        """检查是否可以执行某个工具"""
        return self.permissions.can_execute(tool_name, args or {})

    def register_tool(self, tool_name: str, tool_class):
        """注册工具"""
        self.tools.register(tool_name, tool_class)

    def execute_tool(self, tool_name: str, args: dict, context: dict = None):
        """执行工具，带权限检查"""
        if not self.can_execute_tool(tool_name, args):
            raise PermissionError(f"Not allowed to execute {tool_name}")

        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")

        return tool.execute(args, context or {})


# 单例
harness = Harness()


def get_harness() -> Harness:
    """获取Harness单例"""
    return harness


def ensure_memory_dir(memory_dir: str = None) -> str:
    """确保记忆目录存在的便捷函数"""
    return harness.ensure_memory_dir_exists(memory_dir)