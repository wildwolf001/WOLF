"""
Scheduler Service - 任务调度系统

支持定时任务和周期性任务执行
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import json
import os


class JobStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(Enum):
    """触发器类型"""
    CRON = "cron"           # cron表达式
    INTERVAL = "interval"   # 间隔触发
    ONCE = "once"           # 单次执行


@dataclass
class ScheduledJob:
    """调度任务"""
    id: str
    name: str
    prompt: str
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]  # cron表达式或interval秒数
    created_at: str
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    recurring: bool = True
    durable: bool = True  # 是否持久化
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "trigger_type": self.trigger_type.value,
            "trigger_config": self.trigger_config,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "status": self.status.value,
            "recurring": self.recurring,
            "durable": self.durable
        }


class SchedulerService:
    """
    任务调度服务

    支持:
    - Cron表达式调度 (如 "0 9 * * *" 每天9点)
    - 间隔调度 (如每30分钟)
    - 单次执行
    - 持久化任务
    """

    def __init__(self, jobs_file: str = None):
        """
        初始化调度器

        Args:
            jobs_file: 任务持久化文件路径
        """
        self.jobs: Dict[str, ScheduledJob] = {}
        self.jobs_file = jobs_file or self._get_default_jobs_file()
        self._running_jobs: Dict[str, asyncio.Task] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._is_running = False

        # 加载持久化任务
        self._load_jobs()

    def _get_default_jobs_file(self) -> str:
        """获取默认的任务持久化文件路径"""
        data_dir = os.path.join(os.getcwd(), "wolf_data", "schedules")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "schedules.json")

    def _load_jobs(self):
        """加载持久化的任务"""
        if not os.path.exists(self.jobs_file):
            return

        try:
            with open(self.jobs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for job_data in data.get("jobs", []):
                try:
                    job = ScheduledJob(
                        id=job_data["id"],
                        name=job_data["name"],
                        prompt=job_data["prompt"],
                        trigger_type=TriggerType(job_data["trigger_type"]),
                        trigger_config=job_data["trigger_config"],
                        created_at=job_data["created_at"],
                        last_run=job_data.get("last_run"),
                        next_run=job_data.get("next_run"),
                        recurring=job_data.get("recurring", True),
                        durable=job_data.get("durable", True)
                    )
                    self.jobs[job.id] = job
                except Exception:
                    continue

        except Exception:
            pass

    def _save_jobs(self):
        """保存任务到持久化文件"""
        try:
            os.makedirs(os.path.dirname(self.jobs_file), exist_ok=True)
            data = {
                "jobs": [job.to_dict() for job in self.jobs.values() if job.durable]
            }
            with open(self.jobs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def parse_cron(self, expression: str) -> Dict[str, Any]:
        """
        解析cron表达式

        Args:
            expression: cron表达式，格式 "分 时 日 月 周"

        Returns:
            解析后的配置字典
        """
        parts = expression.strip().split()

        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}. Expected 5 parts: min hour day month week")

        config = {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "week": parts[4]
        }

        return config

    def _get_next_cron_time(self, trigger_config: Dict[str, Any]) -> Optional[datetime]:
        """计算下一次cron触发时间（简化实现）"""
        import croniter

        try:
            cron = croniter.croniter(
                f"{trigger_config['minute']} {trigger_config['hour']} {trigger_config['day']} {trigger_config['month']} {trigger_config['week']}",
                datetime.now()
            )
            return cron.get_next(datetime)
        except Exception:
            return None

    def _get_next_interval_time(self, trigger_config: Dict[str, Any]) -> datetime:
        """计算下一次间隔触发时间"""
        seconds = trigger_config.get("seconds", 60)
        from datetime import timedelta
        return datetime.now() + timedelta(seconds=seconds)

    async def start(self):
        """启动调度器"""
        if self._is_running:
            return

        self._is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """停止调度器"""
        self._is_running = False

        # 取消所有运行中的任务
        for task in self._running_jobs.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

    async def _scheduler_loop(self):
        """调度器主循环"""
        while self._is_running:
            try:
                now = datetime.now()

                # 检查每个任务是否应该执行
                for job_id, job in list(self.jobs.items()):
                    if job.status == JobStatus.RUNNING:
                        continue

                    # 计算下一次触发时间
                    if job.trigger_type == TriggerType.CRON:
                        job.next_run = self._get_next_cron_time(job.trigger_config)
                    elif job.trigger_type == TriggerType.INTERVAL:
                        job.next_run = self._get_next_interval_time(job.trigger_config)

                    # 检查是否应该执行
                    if job.next_run and now >= job.next_run:
                        await self._execute_job(job)

                # 每分钟检查一次
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(60)

    async def _execute_job(self, job: ScheduledJob):
        """执行任务"""
        job.status = JobStatus.RUNNING
        job.last_run = datetime.now().isoformat()

        # 创建执行任务
        task = asyncio.create_task(self._run_job(job))
        self._running_jobs[job.id] = task

        try:
            await task
            job.status = JobStatus.COMPLETED if job.recurring else JobStatus.COMPLETED
        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
        except Exception:
            job.status = JobStatus.FAILED

        # 清理运行中的任务
        if job.id in self._running_jobs:
            del self._running_jobs[job.id]

        # 如果非周期任务，标记完成
        if not job.recurring:
            job.status = JobStatus.COMPLETED

    async def _run_job(self, job: ScheduledJob):
        """运行任务的具体逻辑"""
        # 这里应该调用MainAgent或LLM来执行任务
        # 简化实现：只是记录执行
        print(f"[Scheduler] Executing job: {job.name} ({job.id})")
        print(f"[Scheduler] Prompt: {job.prompt}")

        # 实际实现中，这里应该：
        # 1. 调用MainAgent.think(job.prompt)
        # 2. 或者发送消息到消息队列

        return True

    async def create_job(
        self,
        name: str,
        prompt: str,
        trigger_type: str = "cron",
        trigger_config: Dict[str, Any] = None,
        recurring: bool = True,
        durable: bool = True
    ) -> str:
        """
        创建新任务

        Args:
            name: 任务名称
            prompt: 执行提示
            trigger_type: 触发类型 (cron/interval/once)
            trigger_config: 触发配置
            recurring: 是否循环
            durable: 是否持久化

        Returns:
            任务ID
        """
        job_id = str(uuid.uuid4())

        job = ScheduledJob(
            id=job_id,
            name=name,
            prompt=prompt,
            trigger_type=TriggerType(trigger_type),
            trigger_config=trigger_config or {},
            created_at=datetime.now().isoformat(),
            recurring=recurring,
            durable=durable
        )

        self.jobs[job_id] = job

        # 计算下次执行时间
        if trigger_type == "cron":
            job.next_run = self._get_next_cron_time(trigger_config)
        elif trigger_type == "interval":
            job.next_run = self._get_next_interval_time(trigger_config)

        # 持久化
        if durable:
            self._save_jobs()

        return job_id

    async def create_cron_job(
        self,
        name: str,
        prompt: str,
        cron_expression: str,
        recurring: bool = True,
        durable: bool = True
    ) -> str:
        """
        创建Cron任务

        Args:
            name: 任务名称
            prompt: 执行提示
            cron_expression: cron表达式 (如 "0 9 * * *" 每天9点)
            recurring: 是否循环
            durable: 是否持久化

        Returns:
            任务ID
        """
        trigger_config = self.parse_cron(cron_expression)
        return await self.create_job(
            name=name,
            prompt=prompt,
            trigger_type="cron",
            trigger_config=trigger_config,
            recurring=recurring,
            durable=durable
        )

    async def create_interval_job(
        self,
        name: str,
        prompt: str,
        interval_seconds: int,
        recurring: bool = True,
        durable: bool = True
    ) -> str:
        """
        创建间隔任务

        Args:
            name: 任务名称
            prompt: 执行提示
            interval_seconds: 间隔秒数
            recurring: 是否循环
            durable: 是否持久化

        Returns:
            任务ID
        """
        trigger_config = {"seconds": interval_seconds}
        return await self.create_job(
            name=name,
            prompt=prompt,
            trigger_type="interval",
            trigger_config=trigger_config,
            recurring=recurring,
            durable=durable
        )

    def list_jobs(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        return [job.to_dict() for job in self.jobs.values()]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        job = self.jobs.get(job_id)
        return job.to_dict() if job else None

    async def delete_job(self, job_id: str) -> bool:
        """
        删除任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功删除
        """
        if job_id not in self.jobs:
            return False

        # 如果任务正在运行，先取消
        if job_id in self._running_jobs:
            self._running_jobs[job_id].cancel()
            try:
                await self._running_jobs[job_id]
            except asyncio.CancelledError:
                pass
            del self._running_jobs[job_id]

        del self.jobs[job_id]
        self._save_jobs()
        return True

    async def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.PENDING
            return True
        return False

    async def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.PENDING
            return True
        return False


# 单例
scheduler_service = SchedulerService()


async def start_scheduler():
    """启动调度器"""
    await scheduler_service.start()


async def stop_scheduler():
    """停止调度器"""
    await scheduler_service.stop()


async def create_scheduled_task(
    name: str,
    prompt: str,
    trigger_type: str = "cron",
    trigger_config: Dict[str, Any] = None
) -> str:
    """创建调度任务的便捷函数"""
    return await scheduler_service.create_job(name, prompt, trigger_type, trigger_config)


def list_scheduled_tasks() -> List[Dict[str, Any]]:
    """列出所有调度任务"""
    return scheduler_service.list_jobs()


def delete_scheduled_task(job_id: str) -> bool:
    """删除调度任务"""
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(scheduler_service.delete_job(job_id))