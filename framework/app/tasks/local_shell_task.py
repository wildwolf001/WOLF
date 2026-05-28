"""
Local Shell Task - 本地Shell任务执行器
参考 cc-haha-main/src/tasks/LocalShellTask
"""
import asyncio
import os
import signal
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from .base import (
    TaskStateBase,
    TaskType,
    TaskStatus,
    LocalShellSpawnInput,
    SetAppState,
    create_task_state_base
)
from .framework import task_registry
from .output import TaskOutputManager, get_task_output_path
from ..utils.logging import get_logger

logger = get_logger("tasks.local_shell")

@dataclass
class LocalShellTaskState(TaskStateBase):
    """本地Shell任务状态"""
    type: TaskType = field(default=TaskType.LOCAL_BASH)
    status: TaskStatus = field(default=TaskStatus.PENDING)
    command: str = ""
    timeout: Optional[int] = None
    cwd: Optional[str] = None
    return_code: Optional[int] = None
    kind: str = "bash"  # 'bash' | 'monitor'

class LocalShellTask:
    """
    本地Shell任务执行器
    用于在本地执行Shell命令
    """

    def __init__(self, state: LocalShellTaskState):
        self.state = state
        self.output_manager = TaskOutputManager(state.id)
        self._process: Optional[subprocess.Process] = None
        self._abort_event: Optional[asyncio.Event] = None
        self._task: Optional[asyncio.Task] = None

    async def start(
        self,
        set_app_state: Optional[SetAppState] = None,
        abort_event: Optional[asyncio.Event] = None
    ) -> None:
        """启动Shell任务"""
        self._abort_event = abort_event or asyncio.Event()

        # 注册中止信号处理
        self._abort_event.add_done_callback(self._on_abort)

        # 更新状态为running
        await self._update_status(TaskStatus.RUNNING, set_app_state)

        try:
            # 创建进程
            self._process = await asyncio.create_subprocess_shell(
                self.state.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.STDOUT,
                cwd=self.state.cwd,
                env=self._build_env(),
                preexec_fn=os.setsid if os.name != 'nt' else None
            )

            # 使用超时控制读取输出
            read_task = asyncio.create_task(self._read_output())

            # 等待进程结束或中止
            while self._process.returncode is None:
                if self._abort_event.is_set():
                    break
                try:
                    # 每100ms检查一次
                    await asyncio.wait_for(self._process.wait(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

            # 如果被中止，终止进程
            if self._abort_event.is_set():
                await self._kill_process()
                read_task.cancel()
                await self._complete(TaskStatus.KILLED, set_app_state)
                return

            # 等待读取完成
            try:
                await read_task
            except asyncio.CancelledError:
                pass

            # 获取返回码
            self.state.return_code = self._process.returncode

            # 更新为完成状态
            final_status = TaskStatus.COMPLETED if self.state.return_code == 0 else TaskStatus.FAILED
            await self._complete(final_status, set_app_state)

        except asyncio.CancelledError:
            logger.info(f"Shell task cancelled: {self.state.id}")
            await self._kill_process()
            await self._complete(TaskStatus.KILLED, set_app_state)
        except Exception as e:
            logger.error(f"Shell task error: {e}")
            await self._complete(TaskStatus.FAILED, set_app_state, error=str(e))

    async def _read_output(self) -> None:
        """读取进程输出"""
        if not self._process or not self._process.stdout:
            return

        try:
            while True:
                if self._abort_event and self._abort_event.is_set():
                    break

                try:
                    line = await asyncio.wait_for(
                        self._process.stdout.readline(),
                        timeout=0.5
                    )
                except asyncio.TimeoutError:
                    continue

                if not line:
                    break
                await self.output_manager.write(line.decode())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error reading output: {e}")

    async def _kill_process(self) -> None:
        """终止进程"""
        if self._process:
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                else:
                    self._process.terminate()

                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                    else:
                        self._process.kill()
            except Exception as e:
                logger.error(f"Failed to kill process: {e}")

    def _build_env(self) -> dict:
        """构建环境变量"""
        return dict(os.environ)

    def _on_abort(self) -> None:
        """中止回调"""
        if self._task and not self._task.done():
            self._task.cancel()

    async def _update_status(self, status: TaskStatus, set_app_state: Optional[SetAppState]) -> None:
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
        set_app_state: Optional[SetAppState],
        error: Optional[str] = None
    ) -> None:
        """完成任务"""
        self.state.status = status
        self.state.end_time = datetime.utcnow()

        await task_registry.update(self.state.id, lambda t: self.state)

        if set_app_state:
            set_app_state(lambda prev: {
                **prev,
                'tasks': {**prev.get('tasks', {}), self.state.id: self.state.to_dict()}
            })

    @staticmethod
    async def kill(task_id: str, set_app_state: Optional[SetAppState] = None) -> None:
        """终止任务"""
        task = await task_registry.get(task_id)
        if task and isinstance(task, LocalShellTaskState):
            logger.info(f"Killing shell task: {task_id}")
            task.status = TaskStatus.KILLED
            task.end_time = datetime.utcnow()
            await task_registry.update(task_id, lambda t: task)

            if set_app_state:
                set_app_state(lambda prev: {
                    **prev,
                    'tasks': {**prev.get('tasks', {}), task_id: task.to_dict()}
                })


async def create_local_shell_task(
    command: str,
    description: str,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
    tool_use_id: Optional[str] = None,
    kind: str = "bash"
) -> LocalShellTask:
    """创建本地Shell任务"""
    from .base import generate_task_id
    task_id = generate_task_id(TaskType.LOCAL_BASH)

    state = LocalShellTaskState(
        id=task_id,
        type=TaskType.LOCAL_BASH,
        status=TaskStatus.PENDING,
        description=description,
        command=command,
        timeout=timeout,
        cwd=cwd,
        tool_use_id=tool_use_id,
        kind=kind,
        output_file=get_task_output_path(task_id)
    )

    await task_registry.register(state)
    return LocalShellTask(state)


async def run_shell_command(
    command: str,
    description: str = "",
    timeout: int = 30,
    cwd: Optional[str] = None
) -> tuple[int, str]:
    """
    运行Shell命令的便捷函数
    返回 (return_code, output)
    """
    task = await create_local_shell_task(
        command=command,
        description=description or command,
        timeout=timeout,
        cwd=cwd
    )

    abort_event = asyncio.Event()

    # 设置超时
    if timeout:
        async def timeout_handler():
            await asyncio.sleep(timeout)
            abort_event.set()

        asyncio.create_task(timeout_handler())

    await task.start(abort_event=abort_event)

    output = await task.output_manager.read()
    return task.state.return_code or -1, output