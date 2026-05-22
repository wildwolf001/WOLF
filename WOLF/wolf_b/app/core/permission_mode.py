"""
权限模式 - 参考 Claude Code 的权限系统

定义权限模式和行为的枚举类型
"""
from enum import Enum
from typing import List


class PermissionMode(str, Enum):
    """
    权限模式 - 控制权限检查的整体行为

    - default: 默认模式，每次需要权限时向用户请求确认
    - plan: 计划模式，只分析不执行任何操作
    - acceptEdits: 自动接受所有编辑操作
    - bypassPermissions: 绕过所有权限检查（危险，仅用于特殊场景）
    - dontAsk: 不询问，直接拒绝所有需要权限的操作
    """
    DEFAULT = "default"
    PLAN = "plan"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS = "bypassPermissions"
    DONT_ASK = "dontAsk"

    @classmethod
    def all_modes(cls) -> List["PermissionMode"]:
        """获取所有权限模式"""
        return [cls.DEFAULT, cls.PLAN, cls.ACCEPT_EDITS, cls.BYPASS, cls.DONT_ASK]

    @classmethod
    def from_string(cls, value: str) -> "PermissionMode":
        """从字符串转换为权限模式"""
        value = value.lower().strip()
        for mode in cls.all_modes():
            if mode.value.lower() == value or mode.name.lower() == value:
                return mode
        return cls.DEFAULT

    def is_interactive(self) -> bool:
        """是否需要用户交互"""
        return self == PermissionMode.DEFAULT

    def allows_execution(self) -> bool:
        """是否允许执行操作"""
        return self in (PermissionMode.DEFAULT, PermissionMode.ACCEPT_EDITS, PermissionMode.BYPASS)


class PermissionBehavior(str, Enum):
    """
    权限行为 - 定义单个权限规则的预期行为

    - allow: 允许操作
    - deny: 拒绝操作
    - ask: 需要向用户请求确认
    """
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionAction(str, Enum):
    """
    权限动作 - 定义需要权限的操作类型
    """
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"
    EXECUTE = "execute"
    NETWORK = "network"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    def to_color(self) -> str:
        """获取用于终端显示的颜色"""
        colors = {
            RiskLevel.LOW: "green",
            RiskLevel.MEDIUM: "yellow",
            RiskLevel.HIGH: "red"
        }
        return colors.get(self, "white")