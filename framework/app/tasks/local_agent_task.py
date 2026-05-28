"""
Local Agent Task - 本地Agent任务执行器
参考 cc-haha-main/src/tasks/LocalAgentTask/LocalAgentTask.tsx
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime

from .base import TaskStateBase, TaskType, TaskStatus, generate_task_id
from .framework import task_registry
from .output import TaskOutputManager, get_task_output_path
from ..tools.agent.definitions import AgentDefinition, AgentProgress
from ..utils.logging import get_logger

logger = get_logger("tasks.local_agent")

@dataclass
class LocalAgentTaskState(TaskStateBase):
    """本地Agent任务状态"""
    type: TaskType = field(default=TaskType.LOCAL_AGENT)
    status: TaskStatus = field(default=TaskStatus.PENDING)
    agent_id: str = ""
    prompt: str = ""
    selected_agent: Optional[AgentDefinition] = None
    agent_type: str = "general-purpose"
    model: Optional[str] = None
    abort_event: Optional[asyncio.Event] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    progress: Optional[AgentProgress] = None
    retrieved: bool = False
    messages: Optional[List[Dict]] = None
    last_reported_tool_count: int = 0
    last_reported_token_count: int = 0
    isolation: Optional[str] = None  # "auto" | "host" | "docker"
    is_backgrounded: bool = False
    retain: bool = False
    disk_loaded: bool = False
    pending_messages: List[str] = field(default_factory=list)

@dataclass
class ProgressTracker:
    """进度追踪器"""
    tool_use_count: int = 0
    latest_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    recent_activities: List[Dict[str, Any]] = field(default_factory=list)

class LocalAgentTask:
    """
    本地Agent任务执行器
    用于在本地执行Agent任务
    """

    def __init__(self, state: LocalAgentTaskState):
        self.state = state
        self.output_manager = TaskOutputManager(state.id)
        self.progress_tracker = ProgressTracker()
        self._engine: Optional[Any] = None
        self._task: Optional[asyncio.Task] = None

    async def start(
        self,
        set_app_state: Optional[Callable] = None,
        abort_event: Optional[asyncio.Event] = None
    ) -> None:
        """启动Agent任务"""
        self.state.abort_event = abort_event or asyncio.Event()

        # 更新状态为running
        await self._update_status(TaskStatus.RUNNING, set_app_state)

        try:
            # 输出开始信息
            await self.output_manager.write(f"[Agent] Starting task: {self.state.description}\n")
            await self.output_manager.write(f"[Agent] Type: {self.state.agent_type}\n")
            await self.output_manager.write(f"[Agent] Prompt: {self.state.prompt[:200]}...\n")
            
            # 模拟Agent执行
            # 实际实现应该调用QueryEngine
            await self._run_agent()
            
            # 完成
            await self._complete(TaskStatus.COMPLETED, set_app_state)

        except asyncio.CancelledError:
            logger.info(f"Agent task cancelled: {self.state.id}")
            await self._complete(TaskStatus.KILLED, set_app_state)
        except Exception as e:
            logger.error(f"Agent task error: {e}")
            await self.output_manager.write(f"[Agent] Error: {str(e)}\n")
            await self._complete(TaskStatus.FAILED, set_app_state, error=str(e))

    async def _run_agent(self) -> None:
        """运行Agent — 调用 QueryEngine 执行 LLM + 工具循环"""
        from ..query.engine import QueryEngine, Message
        from ..query.config import QueryConfig

        # 确定工作目录
        import os as _os
        project_root = _os.path.join(_os.path.dirname(__file__), '..')
        temp_dir = _os.path.join(project_root, 'temp')
        _os.makedirs(temp_dir, exist_ok=True)

        # 构建 agent 的系统提示
        agent_def = self.state.selected_agent
        system_prompt = ""
        if agent_def and agent_def.system_prompt:
            system_prompt = agent_def.system_prompt
        else:
            system_prompt = f"You are a {self.state.agent_type} agent. Execute the assigned task thoroughly and report results."

        # 添加任务提示
        system_prompt += f"\n\n## Your Task\n{self.state.prompt}"
        system_prompt += f"\n\n## Working Directory\nYou are working in: {temp_dir}"
        system_prompt += "\nReport your complete findings when done. Be thorough."

        # 构建消息
        messages = [
            Message(role="user", content=self.state.prompt)
        ]

        # 获取工具
        from ..tools import tool_registry
        all_tools = [t.to_dict() for t in tool_registry.list_tools()]

        # 如果启用了沙箱隔离，通过自定义 LLM provider 注入沙箱上下文
        isolation_mode = getattr(self.state, 'isolation', None)
        sandbox = None
        if isolation_mode:
            try:
                from ..sandbox import SandboxExecutor
                sandbox = SandboxExecutor(
                    mode=isolation_mode,
                    project_root=_os.path.dirname(temp_dir),
                    temp_dir=temp_dir
                )
                await self.output_manager.write(f"[Agent] Sandbox: {sandbox.mode} mode\n")
                # 在系统提示中告知可使用沙箱
                system_prompt += f"\n\n## Sandbox Available\n"
                system_prompt += f"You are running in `{sandbox.mode}` sandbox mode. "
                system_prompt += "For running code to verify results, use Bash commands directly. "
                if sandbox.mode == "docker":
                    system_prompt += "The code will run in an isolated Docker container. "
                    system_prompt += "Project files are at `/workspace` (read-only). "
                    system_prompt += "Write output files to the current directory (read-write)."
            except Exception as e:
                await self.output_manager.write(f"[Agent] Sandbox init failed: {e}\n")

        # 限制 agent 最大轮数
        config = QueryConfig()
        config.max_turns = 8  # agent 不需要太多轮
        config.max_tokens = 4096

        # 创建引擎
        engine = QueryEngine(
            workspace_path=temp_dir,
            config=config,
            memory_dir=None  # agent 不需要记忆注入
        )

        await self.output_manager.write(f"[Agent] Starting QueryEngine with {len(all_tools)} tools, max_turns={config.max_turns}\n")

        try:
            agent_response = ""
            tool_count = 0

            async for event in engine.query(
                messages=messages,
                system_prompt=system_prompt,
                tools=all_tools
            ):
                # 检查中止
                if self.state.abort_event and self.state.abort_event.is_set():
                    raise asyncio.CancelledError()

                if event.type == "content":
                    text = event.data.get("text", "")
                    agent_response += text
                    await self.output_manager.write(text)

                elif event.type == "tool_start":
                    tool_count += 1
                    tool_name = event.data.get("tool", "unknown")
                    await self.output_manager.write(f"\n[Tool] {tool_name}...\n")

                elif event.type == "tool_result":
                    result = event.data.get("result", "")
                    success = event.data.get("success", True)
                    if not success:
                        await self.output_manager.write(f"[Tool Result] FAILED: {event.data.get('error', '')}\n")

                elif event.type == "thinking_complete":
                    break

            # 保存结果
            self.state.result = {
                "agent_type": self.state.agent_type,
                "response": agent_response[:5000],
                "tool_count": tool_count,
                "success": True
            }
            await self.output_manager.write(f"\n[Agent] Complete: {tool_count} tools used, {len(agent_response)} chars response\n")

        except Exception as e:
            await self.output_manager.write(f"\n[Agent] Execution error: {e}\n")
            self.state.result = {
                "agent_type": self.state.agent_type,
                "error": str(e),
                "success": False
            }
            raise

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
        await self.output_manager.write(f"[Agent] Task {status.value}\n")

        if set_app_state:
            set_app_state(lambda prev: {
                **prev,
                'tasks': {**prev.get('tasks', {}), self.state.id: self.state.to_dict()}
            })

    @staticmethod
    async def kill(task_id: str, set_app_state: Optional[Callable] = None) -> None:
        """终止任务"""
        task = await task_registry.get(task_id)
        if task and isinstance(task, LocalAgentTaskState):
            logger.info(f"Killing agent task: {task_id}")
            task.status = TaskStatus.KILLED
            task.end_time = datetime.utcnow()
            await task_registry.update(task_id, lambda t: task)

            if set_app_state:
                set_app_state(lambda prev: {
                    **prev,
                    'tasks': {**prev.get('tasks', {}), task_id: task.to_dict()}
                })


async def create_local_agent_task(
    prompt: str,
    description: str,
    agent_type: str = "general-purpose",
    model: Optional[str] = None,
    agent_def: Optional[AgentDefinition] = None
) -> LocalAgentTask:
    """创建本地Agent任务"""
    task_id = generate_task_id(TaskType.LOCAL_AGENT)
    agent_id = str(uuid.uuid4()) if hasattr(uuid, 'uuid4') else f"agent_{task_id}"

    state = LocalAgentTaskState(
        id=task_id,
        type=TaskType.LOCAL_AGENT,
        status=TaskStatus.PENDING,
        description=description,
        agent_id=agent_id,
        prompt=prompt,
        agent_type=agent_type,
        model=model,
        selected_agent=agent_def,
        output_file=get_task_output_path(task_id)
    )

    await task_registry.register(state)
    return LocalAgentTask(state)
