"""Built-in Commands - 内置命令模块"""
from ..registry import Command, CommandType

# Git Commands
from .commit import commit_command
from .branch import branch_command
from .diff import diff_command
from .status import status_command

# Task Commands
from .tasks import tasks_command

# Agent Commands
from .agent import agent_command

# File Commands
from .read import read_command
from .edit import edit_command
from .write import write_command

# Session Commands
from .session import session_command
from .history import history_command

def register_all_commands():
    """注册所有内置命令"""
    from ..registry import command_registry
    
    commands = [
        commit_command,
        branch_command,
        diff_command,
        status_command,
        tasks_command,
        agent_command,
        read_command,
        edit_command,
        write_command,
        session_command,
        history_command,
    ]
    
    for cmd in commands:
        if cmd:
            command_registry.register(cmd)

__all__ = [
    'register_all_commands',
    'commit_command',
    'branch_command', 
    'diff_command',
    'status_command',
    'tasks_command',
    'agent_command',
    'read_command',
    'edit_command',
    'write_command',
    'session_command',
    'history_command',
]
