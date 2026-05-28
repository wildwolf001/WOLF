"""
Command Registry - 命令注册表
参考 cc-haha-main/src/commands.ts
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List, Awaitable
from enum import Enum
import asyncio

class CommandType(str, Enum):
    """命令类型"""
    PROMPT = "prompt"       # 交互式提示命令
    BUILTIN = "builtin"    # 内置命令
    SLASH = "slash"        # 斜线命令

@dataclass
class Command:
    """
    命令定义
    对应 CC 的 Command 接口
    """
    name: str
    description: str
    command_type: CommandType = CommandType.BUILTIN
    source: str = "builtin"
    content_length: int = 0
    progress_message: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    # 异步获取命令提示的函数
    get_prompt: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Optional[str]]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'description': self.description,
            'type': self.command_type.value,
            'source': self.source,
        }

class CommandRegistry:
    """
    命令注册表
    管理所有可用命令
    """

    def __init__(self):
        self._commands: Dict[str, Command] = {}
        self._slash_commands: Dict[str, Command] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command name
        self._lock = asyncio.Lock()

    def register(self, command: Command) -> None:
        """注册命令"""
        self._commands[command.name] = command
        
        # 注册斜线命令
        if command.command_type == CommandType.SLASH:
            self._slash_commands[command.name] = command
        
        # 注册别名
        for alias in command.aliases:
            self._aliases[alias] = command.name

    def get(self, name: str) -> Optional[Command]:
        """获取命令"""
        # 检查别名
        if name in self._aliases:
            name = self._aliases[name]
        return self._commands.get(name)

    def get_by_alias(self, alias: str) -> Optional[Command]:
        """通过别名获取命令"""
        real_name = self._aliases.get(alias)
        if real_name:
            return self._commands.get(real_name)
        return None

    def list_all(self) -> List[Command]:
        """列出所有命令"""
        return list(self._commands.values())

    def list_slash_commands(self) -> List[Command]:
        """列出斜线命令"""
        return list(self._slash_commands.values())

    def list_builtins(self) -> List[Command]:
        """列出内置命令"""
        return [c for c in self._commands.values() if c.source == "builtin"]

    async def execute(
        self,
        name: str,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """执行命令"""
        command = self.get(name)
        if not command:
            raise ValueError(f"Command not found: {name}")

        if command.get_prompt:
            return await command.get_prompt(args, context)
        
        # 如果没有 get_prompt，返回 None
        return None

    def has(self, name: str) -> bool:
        """检查命令是否存在"""
        return name in self._commands or name in self._aliases

    def unregister(self, name: str) -> bool:
        """注销命令"""
        if name in self._commands:
            command = self._commands[name]
            del self._commands[name]
            
            if command.command_type == CommandType.SLASH:
                self._slash_commands.pop(name, None)
            
            for alias in command.aliases:
                self._aliases.pop(alias, None)
            return True
        return False

# 全局注册表实例
command_registry = CommandRegistry()

def get_command(name: str) -> Optional[Command]:
    """获取命令的便捷函数"""
    return command_registry.get(name)

def has_command(name: str) -> bool:
    """检查命令是否存在的便捷函数"""
    return command_registry.has(name)

def list_commands() -> List[Command]:
    """列出所有命令的便捷函数"""
    return command_registry.list_all()

def list_slash_commands() -> List[Command]:
    """列出斜线命令的便捷函数"""
    return command_registry.list_slash_commands()
