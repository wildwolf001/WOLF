"""
Task Framework - 任务注册和状态管理框架
参考 cc-haha-main/src/utils/task/framework.ts
"""
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field

from .base import (
    TaskStateBase, 
    TaskStatus, 
    TaskType,
    generate_task_id,
    is_terminal_task_status,
    SetAppState
)
from ..utils.logging import get_logger

logger = get_logger("tasks.framework")

# 常量定义
POLL_INTERVAL_MS = 1000
STOPPED_DISPLAY_MS = 3000
PANEL_GRACE_MS = 30000

@dataclass
class TaskAttachment:
    """任务附件 - 用于UI更新"""
    type: str = 'task_status'
    task_id: str = ''
    tool_use_id: Optional[str] = None
    task_type: str = ''
    status: str = ''
    description: str = ''
    delta_summary: Optional[str] = None

class TaskRegistry:
    """
    全局任务注册表
    管理所有任务的状态和生命周期
    """
    def __init__(self):
        self._tasks: Dict[str, TaskStateBase] = {}
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, List[Callable]] = {}

    async def register(self, task: TaskStateBase) -> None:
        """注册新任务"""
        async with self._lock:
            self._tasks[task.id] = task
            logger.info(f"Task registered: {task.id} (type={task.type.value})")
            await self._notify_subscribers(task.id, 'registered', task)

    async def update(
        self, 
        task_id: str, 
        updater: Callable[[TaskStateBase], TaskStateBase]
    ) -> Optional[TaskStateBase]:
        """更新任务状态"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                old_task = task
                updated = updater(task)
                self._tasks[task_id] = updated
                
                # 检查状态变化
                if old_task.status != updated.status:
                    logger.info(f"Task {task_id} status: {old_task.status.value} → {updated.status.value}")
                    await self._notify_subscribers(task_id, 'status_changed', updated)
                
                return updated
            return None

    async def get(self, task_id: str) -> Optional[TaskStateBase]:
        """获取任务"""
        return self._tasks.get(task_id)

    async def list(self, status: Optional[TaskStatus] = None) -> List[TaskStateBase]:
        """列出任务"""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    async def list_by_type(self, task_type: TaskType) -> List[TaskStateBase]:
        """按类型列出任务"""
        return [t for t in self._tasks.values() if t.type == task_type]

    async def count(self, status: Optional[TaskStatus] = None) -> int:
        """统计任务数量"""
        if status:
            return sum(1 for t in self._tasks.values() if t.status == status)
        return len(self._tasks)

    async def evict(self, task_id: str) -> None:
        """驱逐任务"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                del self._tasks[task_id]
                logger.info(f"Task evicted: {task_id}")
                await self._notify_subscribers(task_id, 'evicted', task)

    async def update_from_dict(self, task_id: str, updates: Dict[str, Any]) -> Optional[TaskStateBase]:
        """从字典更新任务"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            return task

    def subscribe(self, task_id: str, callback: Callable) -> None:
        """订阅任务事件"""
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(callback)

    def unsubscribe(self, task_id: str, callback: Callable) -> None:
        """取消订阅"""
        if task_id in self._subscribers:
            self._subscribers[task_id] = [cb for cb in self._subscribers[task_id] if cb != callback]

    async def _notify_subscribers(self, task_id: str, event: str, task: TaskStateBase) -> None:
        """通知订阅者"""
        if task_id in self._subscribers:
            for callback in self._subscribers[task_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event, task)
                    else:
                        callback(event, task)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")

    async def get_or_create(self, task_id: str, factory: Callable[[], TaskStateBase]) -> TaskStateBase:
        """获取或创建任务"""
        async with self._lock:
            if task_id in self._tasks:
                return self._tasks[task_id]
            task = factory()
            self._tasks[task_id] = task
            return task

# 全局注册表实例
task_registry = TaskRegistry()

async def register_task(task: TaskStateBase) -> None:
    """注册任务的便捷函数"""
    await task_registry.register(task)

async def update_task_state(
    task_id: str,
    updater: Callable[[TaskStateBase], TaskStateBase]
) -> Optional[TaskStateBase]:
    """更新任务状态的便捷函数"""
    return await task_registry.update(task_id, updater)

async def get_task(task_id: str) -> Optional[TaskStateBase]:
    """获取任务的便捷函数"""
    return await task_registry.get(task_id)

async def list_tasks(status: Optional[TaskStatus] = None) -> List[TaskStateBase]:
    """列出任务的便捷函数"""
    return await task_registry.list(status)

async def evict_task(task_id: str) -> None:
    """驱逐任务的便捷函数"""
    await task_registry.evict(task_id)

async def get_task_output_delta(task_id: str, last_offset: int) -> str:
    """获取任务输出的增量"""
    from .output import TaskOutputManager
    manager = TaskOutputManager(task_id)
    return await manager.read(offset=last_offset)
