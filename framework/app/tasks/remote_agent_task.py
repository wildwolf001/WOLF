"""
Remote Agent Task - 远程Agent任务执行器
参考 cc-haha-main/src/tasks/RemoteAgentTask/RemoteAgentTask.ts
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from .base import TaskStateBase, TaskType, TaskStatus, generate_task_id
from .framework import task_registry
from .output import TaskOutputManager, get_task_output_path
from ..utils.logging import get_logger

logger = get_logger("tasks.remote_agent")

@dataclass
class RemoteAgentTaskState(TaskStateBase):
    """远程Agent任务状态"""
    type: TaskType = field(default=TaskType.REMOTE_AGENT)
    status: TaskStatus = field(default=TaskStatus.PENDING)
    agent_id: str = ""
    session_url: Optional[str] = None
    task_session_id: Optional[str] = None
    remote_host: Optional[str] = None
    workspace_id: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class RemoteAgentTask:
    """
    远程Agent任务执行器
    用于在远程CCR环境执行Agent任务
    """

    def __init__(self, state: RemoteAgentTaskState):
        self.state = state
        self.output_manager = TaskOutputManager(state.id)
        self._task: Optional[asyncio.Task] = None
        self._websocket: Optional[Any] = None

    async def start(
        self,
        set_app_state: Optional[Callable] = None,
        abort_event: Optional[asyncio.Event] = None
    ) -> None:
        """启动远程Agent任务"""
        self.state.abort_event = abort_event or asyncio.Event()

        # 更新状态为running
        await self._update_status(TaskStatus.RUNNING, set_app_state)

        try:
            # 连接远程会话
            await self.output_manager.write(f"[RemoteAgent] Connecting to {self.state.session_url}...\n")
            
            # 建立WebSocket连接
            connected = await self._connect_remote()
            
            if not connected:
                raise Exception("Failed to connect to remote session")

            # 执行远程任务
            await self._run_remote_agent()

            # 完成
            await self._complete(TaskStatus.COMPLETED, set_app_state)

        except asyncio.CancelledError:
            logger.info(f"Remote agent task cancelled: {self.state.id}")
            await self._disconnect()
            await self._complete(TaskStatus.KILLED, set_app_state)
        except Exception as e:
            logger.error(f"Remote agent task error: {e}")
            await self.output_manager.write(f"[RemoteAgent] Error: {str(e)}\n")
            await self._complete(TaskStatus.FAILED, set_app_state, error=str(e))

    async def _connect_remote(self) -> bool:
        """
        连接远程会话
        这是一个stub实现
        实际应该建立WebSocket连接
        """
        # 模拟连接延迟
        await asyncio.sleep(0.5)
        
        # 这里应该实际建立WebSocket连接
        # 由于是stub实现，始终返回True
        logger.info(f"[RemoteAgent] Connected (stub)")
        return True

    async def _run_remote_agent(self) -> None:
        """
        运行远程Agent
        这是一个stub实现
        """
        # 模拟执行
        await asyncio.sleep(1)
        await self.output_manager.write(f"[RemoteAgent] Task sent to remote\n")
        await self.output_manager.write(f"[RemoteAgent] Waiting for response...\n")
        
        # 模拟接收响应
        await asyncio.sleep(0.5)
        await self.output_manager.write(f"[RemoteAgent] Response received\n")

    async def _disconnect(self) -> None:
        """断开远程连接"""
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.error(f"Error closing websocket: {e}")
            self._websocket = None

    async def _update_status(self, status: TaskStatus, set_app_state: Optional[Callable]) -> None:
        """更新任务状态"""
        self.state.status = status
        await task_registry.update(self.state.id, lambda t: self.state)

        if set_app_state:
            set_app_state(lambda prev: {
                **prev,
                'tasks': {**prev.get('tasks', {}), self.state.id: self.state.to_dict()}
            })

    async def _complete(
        self,
        status: TaskStatus,
        set_app_state: Optional[Callable],
        error: Optional[str] = None
    ) -> None:
        """完成任务"""
        self.state.status = status
        self.state.end_time = datetime.utcnow()
        if error:
            self.state.error = error

        await task_registry.update(self.state.id, lambda t: self.state)
        await self.output_manager.write(f"[RemoteAgent] Task {status.value}\n")

        await self._disconnect()

        if set_app_state:
            set_app_state(lambda prev: {
                **prev,
                'tasks': {**prev.get('tasks', {}), self.state.id: self.state.to_dict()}
            })

    @staticmethod
    async def kill(task_id: str, set_app_state: Optional[Callable] = None) -> None:
        """终止任务"""
        task = await task_registry.get(task_id)
        if task and isinstance(task, RemoteAgentTaskState):
            logger.info(f"Killing remote agent task: {task_id}")
            task.status = TaskStatus.KILLED
            task.end_time = datetime.utcnow()
            await task_registry.update(task_id, lambda t: task)

            if set_app_state:
                set_app_state(lambda prev: {
                    **prev,
                    'tasks': {**prev.get('tasks', {}), task_id: task.to_dict()}
                })


async def create_remote_agent_task(
    prompt: str,
    description: str,
    session_url: str,
    agent_id: Optional[str] = None,
    remote_host: Optional[str] = None
) -> RemoteAgentTask:
    """创建远程Agent任务"""
    task_id = generate_task_id(TaskType.REMOTE_AGENT)
    agent_id = agent_id or str(uuid.uuid4())

    state = RemoteAgentTaskState(
        id=task_id,
        type=TaskType.REMOTE_AGENT,
        status=TaskStatus.PENDING,
        description=description,
        agent_id=agent_id,
        session_url=session_url,
        remote_host=remote_host,
        output_file=get_task_output_path(task_id)
    )

    await task_registry.register(state)
    return RemoteAgentTask(state)
