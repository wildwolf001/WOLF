"""
PermissionManager - 权限管理器

管理工具执行权限
"""
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum


class PermissionLevel(Enum):
    """权限级别"""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4


@dataclass
class PermissionRule:
    """权限规则"""
    tool_name: str
    allowed: bool
    conditions: Dict[str, Any] = field(default_factory=dict)
    args_schema: Optional[str] = None


class PermissionManager:
    """
    权限管理器

    管理哪些工具可以被执行，以及执行的条件
    """

    def __init__(self):
        self._rules: Dict[str, PermissionRule] = {}
        self._allowed_paths: Set[str] = set()
        self._blocked_paths: Set[str] = set()
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认权限规则"""
        # 默认允许的基础工具
        default_allowed = [
            "read", "write", "edit", "delete",
            "list", "glob", "grep",
            "bash", "execute"
        ]

        for tool in default_allowed:
            self._rules[tool] = PermissionRule(
                tool_name=tool,
                allowed=True
            )

        # 默认阻止的危险操作
        default_blocked = [
            "rm -rf", "format", "del /f", "mkfs"
        ]

        # 这些通过条件检查而不是完全阻止

    def add_allowed_path(self, path: str):
        """
        添加允许的路径

        Args:
            path: 路径
        """
        self._allowed_paths.add(path)

    def add_blocked_path(self, path: str):
        """
        添加阻止的路径

        Args:
            path: 路径
        """
        self._blocked_paths.add(path)

    def can_execute(self, tool_name: str, args: Dict[str, Any] = None) -> bool:
        """
        检查是否允许执行工具

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            是否允许执行
        """
        # 检查是否有明确规则
        rule = self._rules.get(tool_name)
        if rule:
            if not rule.allowed:
                return False

            # 检查条件
            if rule.conditions:
                return self._check_conditions(rule.conditions, args or {})

        # 默认允许（如果没设置规则）
        return True

    def _check_conditions(self, conditions: Dict[str, Any], args: Dict[str, Any]) -> bool:
        """检查条件是否满足"""
        # 路径条件检查
        if "allowed_paths" in conditions:
            path = args.get("path", "")
            if path:
                # 检查路径是否在允许列表中
                path_allowed = any(path.startswith(allowed) for allowed in conditions["allowed_paths"])
                if not path_allowed:
                    return False

        # 阻止路径检查
        if "blocked_paths" in conditions:
            path = args.get("path", "")
            if path:
                for blocked in conditions["blocked_paths"]:
                    if blocked in path:
                        return False

        return True

    def set_rule(self, tool_name: str, allowed: bool, conditions: Dict[str, Any] = None):
        """
        设置工具权限规则

        Args:
            tool_name: 工具名称
            allowed: 是否允许
            conditions: 条件字典
        """
        self._rules[tool_name] = PermissionRule(
            tool_name=tool_name,
            allowed=allowed,
            conditions=conditions or {}
        )

    def get_rule(self, tool_name: str) -> Optional[PermissionRule]:
        """获取工具权限规则"""
        return self._rules.get(tool_name)

    def list_rules(self) -> List[Dict[str, Any]]:
        """列出所有权限规则"""
        return [
            {
                "tool_name": rule.tool_name,
                "allowed": rule.allowed,
                "conditions": rule.conditions
            }
            for rule in self._rules.values()
        ]

    def reset(self):
        """重置所有权限规则"""
        self._rules.clear()
        self._init_default_rules()