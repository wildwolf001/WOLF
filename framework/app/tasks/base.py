"""
Task Base - 任务系统基础定义
参考 cc-haha-main/src/Task.ts
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Any, Dict
import asyncio
import uuid
import os

# Task ID prefix mapping
TASK_ID_PREFIXES = {
    'local_bash': 'b',
    'local_agent': 'a',
    'remote_agent': 'r',
    'in_process_teammate': 't',
    'local_workflow': 'w',
    'monitor_mcp': 'm',
    'dream': 'd',
}

class TaskType(str, Enum):
    """任务类型枚举"""
    LOCAL_BASH = 'local_bash'
    LOCAL_AGENT = 'local_agent'
    REMOTE_AGENT = 'remote_agent'
    IN_PROCESS_TEAMMATE = 'in_process_teammate'
    LOCAL_WORKFLOW = 'local_workflow'
    MONITOR_MCP = 'monitor_mcp'
    DREAM = 'dream'

    @classmethod
    def from_string(cls, value: str) -> 'TaskType':
        """从字符串创建TaskType"""
        try:
            return cls(value)
        except ValueError:
            return cls.LOCAL_BASH

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    KILLED = 'killed'

    def is_terminal(self) -> bool:
        """检查是否为终止状态"""
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED)

def is_terminal_task_status(status: TaskStatus) -> bool:
    """检查状态是否为终止状态"""
    return status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED)

def generate_task_id(task_type: TaskType) -> str:
    """生成任务ID"""
    prefix = TASK_ID_PREFIXES.get(task_type.value, 'x')
    random_part = uuid.uuid4().hex[:8]
    return f"{prefix}{random_part}"

@dataclass
class TaskStateBase:
    """
    任务状态基类
    对应 CC 的 TaskStateBase
    """
    id: str = ''
    type: TaskType = TaskType.LOCAL_BASH
    status: TaskStatus = TaskStatus.PENDING
    description: str = ''
    tool_use_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    output_file: str = ''
    output_offset: int = 0
    notified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'type': self.type.value,
            'status': self.status.value,
            'description': self.description,
            'tool_use_id': self.tool_use_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'output_file': self.output_file,
            'output_offset': self.output_offset,
            'notified': self.notified,
        }

@dataclass
class TaskContext:
    """
    任务执行上下文
    对应 CC 的 TaskContext
    """
    abort_event: asyncio.Event
    get_app_state: Callable[[], Dict[str, Any]]
    set_app_state: Callable[[Callable[[Dict], Dict]], None]

    @property
    def is_aborted(self) -> bool:
        """检查是否已中止"""
        return self.abort_event.is_set()

    def abort(self) -> None:
        """请求中止"""
        self.abort_event.set()

def create_task_state_base(
    id: str,
    task_type: TaskType,
    description: str,
    tool_use_id: Optional[str] = None,
    output_file: str = ''
) -> TaskStateBase:
    """
    创建任务状态基类
    对应 CC 的 createTaskStateBase
    """
    return TaskStateBase(
        id=id,
        type=task_type,
        status=TaskStatus.PENDING,
        description=description,
        tool_use_id=tool_use_id,
        output_file=output_file or get_default_output_path(id),
        start_time=datetime.utcnow()
    )

def get_default_output_path(task_id: str) -> str:
    """获取默认输出路径"""
    cache_dir = os.path.join(os.path.expanduser('~'), '.wolf', 'tasks')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{task_id}.output")

@dataclass
class LocalShellSpawnInput:
    """
    本地Shell任务输入
    对应 CC 的 LocalShellSpawnInput
    """
    command: str
    description: str
    timeout: Optional[int] = None
    tool_use_id: Optional[str] = None
    agent_id: Optional[str] = None
    kind: str = 'bash'  # 'bash' | 'monitor'

@dataclass 
class TaskHandle:
    """
    任务句柄
    对应 CC 的 TaskHandle
    """
    task_id: str
    cleanup: Optional[Callable[[], None]] = None

# Type alias for task types
Task = TaskStateBase
SetAppState = Callable[[Callable[[Dict], Dict]], None]
