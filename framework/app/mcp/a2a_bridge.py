"""Google A2A 协议桥 — Agent-to-Agent 通信"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
import uuid
from datetime import datetime


class TaskStatus(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class AgentCard:
    """Agent 名片 — 服务发现"""
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=list)
    endpoint: str = ""


@dataclass
class A2ATask:
    """A2A 任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: TaskStatus = TaskStatus.SUBMITTED
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class A2AServer:
    """A2A 服务端 — 暴露 WOLF Agent 能力给其他 Agent"""

    def __init__(self, agent_card: AgentCard):
        self.card = agent_card
        self._tasks: Dict[str, A2ATask] = {}

    def get_card(self) -> dict:
        """GET /a2a/agent-card"""
        return {
            "name": self.card.name,
            "description": self.card.description,
            "version": self.card.version,
            "capabilities": self.card.capabilities,
        }

    def submit_task(self, description: str) -> str:
        """POST /a2a/tasks — 其他 Agent 提交任务"""
        task = A2ATask(description=description)
        self._tasks[task.id] = task
        return task.id

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """GET /a2a/tasks/{id}"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return {
            "id": task.id, "status": task.status.value,
            "description": task.description, "result": task.result
        }

    def update_task(self, task_id: str, status: TaskStatus, result: str = None):
        if task_id in self._tasks:
            self._tasks[task_id].status = status
            if result:
                self._tasks[task_id].result = result


class A2AClient:
    """A2A 客户端 — WOLF 调用其他 Agent"""

    def __init__(self):
        self._known_agents: Dict[str, AgentCard] = {}

    async def discover(self, agent_url: str) -> Optional[AgentCard]:
        """发现远程 Agent"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{agent_url}/a2a/agent-card") as resp:
                    data = await resp.json()
                    card = AgentCard(
                        name=data["name"], description=data["description"],
                        version=data.get("version", "1.0.0"),
                        capabilities=data.get("capabilities", []),
                        endpoint=agent_url
                    )
                    self._known_agents[card.name] = card
                    return card
        except Exception:
            return None

    async def submit_task(self, agent_name: str, description: str) -> Optional[str]:
        """向远程 Agent 提交任务"""
        agent = self._known_agents.get(agent_name)
        if not agent:
            return None
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{agent.endpoint}/a2a/tasks",
                    json={"description": description}
                ) as resp:
                    data = await resp.json()
                    return data.get("task_id")
        except Exception:
            return None
