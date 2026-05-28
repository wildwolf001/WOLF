"""
AgentTool - Agent工具实现
参考 cc-haha-main/src/tools/AgentTool/AgentTool.tsx
"""
from typing import Optional, Dict, Any, Callable, Awaitable
import asyncio
import uuid

from .definitions import (
    AgentToolInput,
    AgentToolResult,
    AgentDefinition,
    AgentProgress,
    get_builtin_agent,
)
from ..registry import ToolDefinition, ToolResult, tool_registry, AGENT_TOOL_NAME
from ...tasks.base import TaskType, generate_task_id
from ...tasks.framework import task_registry
from ...tasks.local_agent_task import LocalAgentTaskState, LocalAgentTask
from ...utils.logging import get_logger

logger = get_logger("tools.agent")

class AgentTool:
    """
    Agent工具 - 启动和管理子Agent
    """

    name = AGENT_TOOL_NAME
    description = "Spawn an agent to complete a task"

    input_schema = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "A short (3-5 word) description of the task"
            },
            "prompt": {
                "type": "string",
                "description": "The task for the agent to perform"
            },
            "subagent_type": {
                "type": "string",
                "description": "The type of specialized agent to use"
            },
            "model": {
                "type": "string",
                "enum": ["sonnet", "opus", "haiku"],
                "description": "Model override"
            },
            "run_in_background": {
                "type": "boolean",
                "description": "Run in background"
            },
            "name": {
                "type": "string",
                "description": "Name for the spawned agent"
            },
            "team_name": {
                "type": "string",
                "description": "Team name for spawning"
            },
            "mode": {
                "type": "string",
                "description": "Permission mode for spawned teammate"
            },
            "isolation": {
                "type": "string",
                "enum": ["auto", "host", "docker"],
                "description": "Sandbox isolation mode: auto (docker if available), host (direct), docker (container)"
            },
        },
        "required": ["description", "prompt"]
    }

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ToolResult:
        """执行Agent工具"""
        tool_call_id = context.get("tool_use_id", str(uuid.uuid4()))
        
        try:
            # 解析输入
            input_data = AgentToolInput(
                description=arguments.get("description", ""),
                prompt=arguments.get("prompt", ""),
                subagent_type=arguments.get("subagent_type"),
                model=arguments.get("model"),
                run_in_background=arguments.get("run_in_background", False),
                name=arguments.get("name"),
                team_name=arguments.get("team_name"),
                mode=arguments.get("mode"),
                isolation=arguments.get("isolation"),
            )
            
            # 执行Agent
            result = await self._execute_agent(input_data, context)
            
            return ToolResult(
                tool_call_id=tool_call_id,
                name=self.name,
                result=result.result,
                success=result.status == "completed"
            )
            
        except Exception as e:
            logger.error(f"AgentTool error: {e}")
            return ToolResult(
                tool_call_id=tool_call_id,
                name=self.name,
                result=None,
                success=False,
                error=str(e)
            )

    async def _execute_agent(
        self,
        input_data: AgentToolInput,
        context: Dict[str, Any]
    ) -> AgentToolResult:
        """执行Agent"""
        # 获取Agent定义
        agent_def = self._get_agent_definition(input_data.subagent_type)
        
        # 创建Agent任务
        task_id = generate_task_id(TaskType.LOCAL_AGENT)
        agent_id = str(uuid.uuid4())
        
        # 确定隔离模式
        isolation = input_data.isolation or getattr(agent_def, 'isolation', None)

        # 创建任务状态
        state = LocalAgentTaskState(
            id=task_id,
            type=TaskType.LOCAL_AGENT,
            status="pending",
            description=input_data.description,
            agent_id=agent_id,
            prompt=input_data.prompt,
            agent_type=agent_def.agent_type,
            model=input_data.model or agent_def.model,
            selected_agent=agent_def,
            isolation=isolation,
        )
        
        # 注册任务
        await task_registry.register(state)
        
        logger.info(f"Agent task created: {task_id} (agent_id={agent_id})")
        
        # 如果是后台运行，立即返回
        if input_data.run_in_background:
            return AgentToolResult(
                status="async_launched",
                agent_id=agent_id,
                result=f"Agent started in background: {task_id}"
            )
        
        # 前台运行：创建LocalAgentTask并等待
        agent_task = LocalAgentTask(state)
        abort_event = context.get("abort_event")
        
        try:
            await agent_task.start(abort_event=abort_event)
            
            # 获取结果
            output = await agent_task.output_manager.read()
            
            return AgentToolResult(
                status="completed",
                result=output or f"Agent completed: {input_data.description}",
                agent_id=agent_id
            )
        except asyncio.CancelledError:
            return AgentToolResult(
                status="failed",
                agent_id=agent_id,
                error="Agent cancelled"
            )
        except Exception as e:
            return AgentToolResult(
                status="failed",
                agent_id=agent_id,
                error=str(e)
            )

    def _get_agent_definition(self, agent_type: Optional[str]) -> AgentDefinition:
        """获取Agent定义"""
        if not agent_type:
            return get_builtin_agent("general-purpose")
        
        agent_def = get_builtin_agent(agent_type)
        if agent_def:
            return agent_def
        
        # 默认使用通用Agent
        return get_builtin_agent("general-purpose")


# 注册工具
def register_agent_tool():
    """注册Agent工具"""
    tool_registry.register(
        ToolDefinition(
            name=AGENT_TOOL_NAME,
            description=AgentTool.description,
            input_schema=AgentTool.input_schema,
            function=AgentTool().execute,
            is_read_only=False,
            permission='agent'
        )
    )

# 自动注册
register_agent_tool()
