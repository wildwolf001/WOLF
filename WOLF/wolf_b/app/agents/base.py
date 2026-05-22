"""
BaseAgent - 所有Agent的基类

简化版本：只保留核心属性和方法，移除多Agent协作逻辑。

RESERVED for future extension:
- 单Agent派生子Agent的模式
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    WORKING = "working"
    ANALYZING = "analyzing"


@dataclass
class AgentMessage:
    """消息数据类"""
    id: str
    from_role: str
    to_role: str
    type: str  # task, result, question
    content: str
    timestamp: datetime
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """
    Base Agent - 简化版本

    移除多Agent协作逻辑，只保留核心属性和方法。

    RESERVED for future extension:
    - 单Agent派生子Agent的模式（类似 cc-haha 的 AgentTool）
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        name: str,
        system_prompt: str,
        capabilities: List[str]
    ):
        self.agent_id = agent_id
        self.role = role
        self.name = name
        self.system_prompt = system_prompt
        self.capabilities = capabilities
        self.status = AgentStatus.IDLE
        self.current_task: Optional[str] = None
        self.message_history: List[AgentMessage] = []

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> str:
        """
        执行任务 - 子类必须实现

        Args:
            task: 任务描述字典，包含：
                - description: 任务描述
                - title: 任务标题（可选）
                - 其他自定义字段

        Returns:
            执行结果字符串
        """
        pass

    async def think(self, user_message: str) -> str:
        """
        思考 - 异步执行接口

        默认实现：将user_message包装成task，调用execute
        子类可以覆盖这个来实现更复杂的think逻辑
        """
        task = {
            "description": user_message,
            "title": user_message[:100] if user_message else "Task"
        }
        return await self.execute(task)

    # ==================== 消息处理 ====================

    async def receive(self, message: AgentMessage) -> None:
        """接收消息"""
        self.message_history.append(message)
        self.current_task = message.task_id
        self.status = AgentStatus.ANALYZING

    # ==================== 状态管理 ====================

    def update_status(self, status: str) -> None:
        """更新Agent状态"""
        try:
            self.status = AgentStatus(status)
        except ValueError:
            self.status = AgentStatus.IDLE

    # ==================== 历史记录 ====================

    def get_history(self) -> List[AgentMessage]:
        """获取消息历史"""
        return self.message_history

    def clear_history(self) -> None:
        """清空消息历史"""
        self.message_history = []

    # ==================== 信息查询 ====================

    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "name": self.name,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "current_task": self.current_task,
            "message_count": len(self.message_history)
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(role={self.role}, status={self.status.value})"


# =============================================================================
# RESERVED for future extension:
# 以下是预留的多Agent协作相关代码，当前版本已禁用
# 如需启用多Agent能力，可参考 cc-haha 的 AgentTool 实现
# =============================================================================

# 预留的 Agent 标签系统（未来扩展用）
RESERVED_TAGS = {
    "research": ["research", "information", "paper", "survey", "data_analysis", "literature"],
    "ml": ["machine_learning", "model", "training", "optimization", "algorithm", "deep_learning"],
    "developer": ["code", "backend", "frontend", "api", "database", "implementation", "programming"],
    "writer": ["documentation", "report", "writing", "readme", "docs", "technical_writing"],
    "data": ["data", "dataset", "etl", "processing", "annotation", "data_cleaning"],
    "review": ["review", "quality", "security", "bug", "issue", "code_review", "analysis"],
    "devops": ["deployment", "ci_cd", "infrastructure", "docker", "monitoring", "cloud"],
    "pm": ["planning", "coordination", "task", "schedule", "milestone", "management"],
    "main": ["coordinator", "orchestration", "general"]
}

# 预留的 Agent 协作接口（未来扩展用）
class BaseCollaborationInterface:
    """
    预留的协作接口

    未来如果需要启用多Agent协作，可实现此接口：
    1. 子Agent注册到父Agent
    2. 父Agent派发任务
    3. 子Agent执行后返回结果

    参考 cc-haha 的 AgentTool 实现
    """

    async def register_sub_agent(self, agent_id: str, agent) -> None:
        """注册子Agent"""
        raise NotImplementedError("Future extension: register sub-agent")

    async def dispatch_task(self, task: Dict[str, Any]) -> str:
        """派发任务给子Agent"""
        raise NotImplementedError("Future extension: dispatch task to sub-agent")

    async def collect_results(self) -> List[Dict[str, Any]]:
        """收集子Agent结果"""
        raise NotImplementedError("Future extension: collect results from sub-agents")
