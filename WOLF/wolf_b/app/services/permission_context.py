"""
Permission context - 参照 cc-haha 的 ToolPermissionContext
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class PermissionMode(str, Enum):
    """权限模式 - 参照 cc 的 PermissionMode"""
    DEFAULT = "default"
    BYPASS = "bypass"
    ACCEPT_EDITS = "acceptEdits"
    DONT_ASK = "dontAsk"
    PLAN = "plan"


@dataclass
class AdditionalWorkingDirectory:
    """额外的工作目录条目 - 参照 cc 的 AdditionalWorkingDirectory"""
    path: str
    source: str  # "originalCwd", "cliArg", "userSettings", "session"


@dataclass
class ToolPermissionContext:
    """
    工具权限上下文 - 参照 cc 的 ToolPermissionContext

    用于在工具执行时检查路径权限
    """
    mode: PermissionMode = PermissionMode.DEFAULT
    additional_working_directories: Dict[str, AdditionalWorkingDirectory] = field(default_factory=dict)
    always_allow_rules: dict = field(default_factory=dict)
    always_deny_rules: dict = field(default_factory=dict)
    always_ask_rules: dict = field(default_factory=dict)
    is_bypass_permissions_mode_available: bool = False
    should_avoid_permission_prompts: bool = False
    pre_plan_mode: Optional[PermissionMode] = None

    def add_working_directory(self, path: str, source: str = "session") -> None:
        """添加工作目录"""
        if path and path not in self.additional_working_directories:
            self.additional_working_directories[path] = AdditionalWorkingDirectory(
                path=path,
                source=source
            )

    def get_working_directories(self) -> list:
        """获取所有工作目录"""
        return list(self.additional_working_directories.keys())


def get_empty_permission_context() -> ToolPermissionContext:
    """获取空的权限上下文"""
    return ToolPermissionContext(
        mode=PermissionMode.DEFAULT,
        additional_working_directories={},
        always_allow_rules={},
        always_deny_rules={},
        always_ask_rules={},
        is_bypass_permissions_mode_available=False
    )


def create_permission_context(
    mode: PermissionMode = PermissionMode.DEFAULT,
    working_directories: list = None,
    **kwargs
) -> ToolPermissionContext:
    """创建权限上下文的便捷函数"""
    context = get_empty_permission_context()
    context.mode = mode

    if working_directories:
        for wd in working_directories:
            context.add_working_directory(wd)

    for key, value in kwargs.items():
        if hasattr(context, key):
            setattr(context, key, value)

    return context