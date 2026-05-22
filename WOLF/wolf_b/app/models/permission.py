"""
权限请求/响应模型 - 参考 Claude Code 的权限类型定义
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Awaitable
from enum import Enum
import uuid


class PermissionRequestType(str, Enum):
    """权限请求类型"""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    FILE_DELETE = "file_delete"
    BASH = "bash"
    WEB_FETCH = "web_fetch"
    WEB_SEARCH = "web_search"
    AGENT = "agent"
    OTHER = "other"


class PermissionAction(str, Enum):
    """权限动作"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


@dataclass
class PermissionOption:
    """权限对话框选项"""
    value: str
    label: str
    keybinding: Optional[str] = None  # 快捷键


@dataclass
class PermissionRequest:
    """
    权限请求 - 当工具需要用户授权时创建

    Attributes:
        request_id: 请求的唯一标识
        tool_name: 请求权限的工具名称
        request_type: 请求类型
        description: 人类可读的描述
        path: 相关的文件路径（如果有）
        command: 相关的命令（如果有）
        risk_level: 风险等级 LOW/MEDIUM/HIGH
        options: 可选的响应选项
        created_at: 创建时间戳
    """
    tool_name: str
    request_type: PermissionRequestType
    description: str
    path: Optional[str] = None
    command: Optional[str] = None
    risk_level: str = "MEDIUM"
    options: List[PermissionOption] = field(default_factory=list)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于 JSON 序列化"""
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "request_type": self.request_type.value,
            "description": self.description,
            "path": self.path,
            "command": self.command,
            "risk_level": self.risk_level,
            "options": [
                {
                    "value": opt.value,
                    "label": opt.label,
                    "keybinding": opt.keybinding
                }
                for opt in self.options
            ],
            "created_at": self.created_at
        }

    @classmethod
    def create_default_options(cls) -> List[PermissionOption]:
        """创建默认选项"""
        return [
            PermissionOption(value="allow", label="允许"),
            PermissionOption(value="deny", label="拒绝"),
            PermissionOption(value="allow_always", label="始终允许", keybinding="a"),
            PermissionOption(value="deny_always", label="始终拒绝", keybinding="d"),
        ]


@dataclass
class PermissionResponse:
    """
    用户对权限请求的响应

    Attributes:
        request_id: 对应的请求 ID
        action: 用户选择的动作
        feedback: 用户可选的反馈信息
        timestamp: 响应时间戳
    """
    request_id: str
    action: str  # "allow", "deny", "allow_always", "deny_always"
    feedback: Optional[str] = None
    timestamp: float = field(default_factory=lambda: __import__("time").time())


@dataclass
class PermissionRule:
    """
    权限规则 - 定义特定操作的行为

    Attributes:
        tool_name: 工具名称（可以是 glob pattern）
        behavior: 行为 allow/deny/ask
        source: 规则来源 (userSettings, session, cliArg 等)
        pattern: 可选的路径/内容匹配模式
        persistent: 是否持久化
    """
    tool_name: str
    behavior: str  # "allow", "deny", "ask"
    source: str = "session"
    pattern: Optional[str] = None
    persistent: bool = False

    def matches(self, tool_name: str, path: Optional[str] = None) -> bool:
        """检查规则是否匹配给定的工具和路径"""
        if self.tool_name == tool_name or self.tool_name == "*":
            if self.pattern and path:
                return self.pattern in path
            return True
        return False


@dataclass
class PermissionResult:
    """
    权限检查结果

    Attributes:
        allowed: 是否允许
        reason: 原因说明
        reason_type: 原因类型 (rule, mode, hook 等)
    """
    allowed: bool
    reason: str
    reason_type: str = "other"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "reason_type": self.reason_type
        }