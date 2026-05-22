"""
SharedWorkspace - 共享工作空间 (Blackboard Pattern)

================================================================================
DEPRECATED - 此模块已被废弃
================================================================================

此模块用于多Agent协作的"主持人模式"，已被以下新架构取代：
- app/agents/main_agent.py: 单Agent直接执行模式
- app/services/memory_service.py: 记忆系统

保留此文件是为了未来可能的扩展需求：
- 单Agent派生子Agent的模式
- 未来需要多Agent时的参考实现

当前主流程不再使用此模块。如需重新启用，请联系开发者。

使用方式变更：
- 旧: MainAgent.think() → SharedWorkspace → 多Agent协作
- 新: MainAgent.think() → LLM Loop → Tools → 直接响应

================================================================================
"""

# 硬编码禁用 - 当前版本不支持多Agent协作
ENABLE_SHARED_WORKSPACE = False

if ENABLE_SHARED_WORKSPACE:
    # 仅在明确启用时导入（未来扩展用）
    pass
else:
    # 模块仍然加载但功能被禁用
    class SharedWorkspace:
        """禁用状态 - 请使用新的单Agent架构"""
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "SharedWorkspace is deprecated. "
                "Use MainAgent with single-agent direct execution mode instead."
            )

    def create_workspace_for_task(*args, **kwargs):
        """禁用"""
        raise RuntimeError("SharedWorkspace is deprecated.")

    def get_workspace(*args, **kwargs):
        """禁用"""
        raise RuntimeError("SharedWorkspace is deprecated.")


# 以下是原实现代码，保留作为参考（永不执行）
if ENABLE_SHARED_WORKSPACE and False:
    """
    原有实现代码保留于此：
    - FindingType 枚举
    - Finding 数据类
    - SharedWorkspace 类
    - 所有协作方法

    参考价值：未来如需实现类似协作系统，可参考此实现
    """
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import asyncio
import json


class FindingType(Enum):
    """发现类型"""
    ANNOUNCEMENT = "announcement"      # 公告（如新任务）
    RESEARCH = "research"             # 研究发现
    ANALYSIS = "analysis"             # 分析结果
    CODE = "code"                     # 代码相关
    REVIEW = "review"                 # 审阅意见
    QUESTION = "question"             # 问题
    RESPONSE = "response"             # 回应
    REMINDER = "reminder"             # 提醒
    FINAL = "final"                   # 最终结论


@dataclass
class Finding:
    """一个发现/贡献"""
    id: str
    agent: str                          # 来自哪个Agent
    finding_type: FindingType
    content: str                         # 发现内容
    relevant_tags: List[str] = field(default_factory=list)  # 相关标签
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    original_finding_id: Optional[str] = None  # 如果是回应，指向原发现

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if isinstance(self.finding_type, str):
            self.finding_type = FindingType(self.finding_type)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent": self.agent,
            "type": self.finding_type.value,
            "content": self.content,
            "relevant_tags": self.relevant_tags,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "original_finding_id": self.original_finding_id
        }


@dataclass
class PendingQuestion:
    """待回答的问题"""
    id: str
    from_agent: str
    to_agent: Optional[str]  # None表示广播给所有人
    question: str
    timestamp: str = ""
    answered: bool = False
    answer: Optional[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class Task:
    """任务定义"""
    id: str
    title: str
    description: str
    task_type: str  # research/data/ml/developer/writer/review/devops
    created_by: str
    created_at: str = ""
    deadline: Optional[str] = None
    status: str = "pending"  # pending/in_progress/completed/cancelled
    assigned_agents: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SharedWorkspace:
    """
    共享工作空间 - Agent之间协作的核心机制

    类似于黑板系统，所有Agent可以：
    1. 发布发现（其他Agent可以看到）
    2. 发布问题（直接@某个Agent或广播）
    3. 订阅相关话题（自动收到通知）
    4. 查看所有历史发现

    MainAgent负责：
    - 创建工作空间
    - 发起讨论（发布公告）
    - 收集响应
    - 综合最终报告

    其他Agent可以：
    - 看到公告后主动参与
    - 直接与其他Agent通信
    - 自主决定是否响应某个发现
    """

    _instances: Dict[str, 'SharedWorkspace'] = {}

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.findings: List[Finding] = []
        self.pending_questions: List[PendingQuestion] = []
        self.tasks: Dict[str, Task] = {}
        self.subscribers: Dict[str, Callable] = {}  # agent_role -> callback
        self.observation_end_time: Optional[float] = None
        self.created_at = datetime.now().isoformat()

        # 事件队列，用于异步通知
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

    @classmethod
    async def create(cls, task_id: str, goal: str = "") -> 'SharedWorkspace':
        """
        工厂方法：创建新的工作空间

        Args:
            task_id: 唯一标识
            goal: 任务目标

        Returns:
            新的SharedWorkspace实例
        """
        workspace = cls(task_id)

        # 如果有目标，创建初始任务
        if goal:
            initial_task = Task(
                id=str(uuid.uuid4()),
                title=goal[:100],
                description=goal,
                task_type="coordinator",
                created_by="system"
            )
            workspace.tasks[initial_task.id] = initial_task

        cls._instances[task_id] = workspace

        # 启动事件监听器
        workspace._running = True
        workspace._listener_task = asyncio.create_task(workspace._event_listener())

        return workspace

    @classmethod
    def get(cls, task_id: str) -> Optional['SharedWorkspace']:
        """获取已有的工作空间"""
        return cls._instances.get(task_id)

    @classmethod
    def list_all(cls) -> Dict[str, 'SharedWorkspace']:
        """列出所有工作空间"""
        return cls._instances.copy()

    async def close(self):
        """关闭工作空间"""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self.task_id in self._instances:
            del self._instances[self.task_id]

    # ==================== 发布发现 ====================

    async def post_finding(
        self,
        agent_role: str,
        content: str,
        finding_type: FindingType = FindingType.ANALYSIS,
        relevant_tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        original_finding_id: Optional[str] = None
    ) -> Finding:
        """
        Agent发布一个发现

        所有订阅该话题的Agent都会收到通知

        Args:
            agent_role: 发布者的角色
            content: 发现内容
            finding_type: 发现类型
            relevant_tags: 相关标签（如["security", "backend"]）
            metadata: 额外元数据
            original_finding_id: 如果是回应，指向原发现ID

        Returns:
            创建的Finding对象
        """
        finding = Finding(
            id=str(uuid.uuid4()),
            agent=agent_role,
            finding_type=finding_type,
            content=content,
            relevant_tags=relevant_tags or [],
            metadata=metadata or {},
            original_finding_id=original_finding_id
        )

        self.findings.append(finding)

        # 异步通知订阅者
        await self._notify_subscribers(finding)

        return finding

    # ==================== 问题通信 ====================

    async def post_question(
        self,
        from_agent: str,
        question: str,
        to_agent: Optional[str] = None,
        relevant_tags: Optional[List[str]] = None
    ) -> PendingQuestion:
        """
        Agent发布一个问题

        Args:
            from_agent: 提问者
            question: 问题内容
            to_agent: 回答者（None表示广播给所有人）
            relevant_tags: 相关标签

        Returns:
            创建的PendingQuestion对象
        """
        pending_q = PendingQuestion(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            question=question
        )

        self.pending_questions.append(pending_q)

        # 如果指定了回答者，直接通知
        if to_agent:
            await self._notify_agent(to_agent, {
                "type": "question",
                "question": pending_q
            })
        else:
            # 广播给所有人
            await self._broadcast({
                "type": "broadcast_question",
                "question": pending_q.to_dict() if hasattr(pending_q, 'to_dict') else str(pending_q)
            })

        return pending_q

    async def answer_question(
        self,
        question_id: str,
        answer: str,
        answering_agent: str
    ) -> bool:
        """
        回答一个待解决的问题

        Args:
            question_id: 问题ID
            answer: 答案
            answering_agent: 回答者

        Returns:
            是否成功找到并更新问题
        """
        for pq in self.pending_questions:
            if pq.id == question_id:
                pq.answered = True
                pq.answer = answer

                # 通知提问者
                await self._notify_agent(pq.from_agent, {
                    "type": "answer",
                    "question_id": question_id,
                    "answer": answer,
                    "from": answering_agent
                })

                # 同时把答案作为发现发布
                await self.post_finding(
                    agent_role=answering_agent,
                    content=f"回答问题: {pq.question}\n\n答案: {answer}",
                    finding_type=FindingType.RESPONSE,
                    relevant_tags=["question_answer"]
                )

                return True
        return False

    # ==================== 订阅机制 ====================

    async def subscribe(self, agent_role: str, callback: Callable[[Finding], Awaitable[None]]):
        """
        Agent订阅工作空间

        当有新的相关发现时，会自动调用callback

        Args:
            agent_role: 订阅的Agent角色
            callback: 收到新发现时的回调函数
        """
        self.subscribers[agent_role] = callback

    async def unsubscribe(self, agent_role: str):
        """取消订阅"""
        if agent_role in self.subscribers:
            del self.subscribers[agent_role]

    def get_agent_relevant_tags(self, agent_role: str) -> List[str]:
        """
        获取与某Agent相关的标签

        子类可以覆盖这个来实现更智能的过滤
        """
        # Agent角色到相关标签的映射
        tag_map = {
            "research": ["research", "information", "paper", "survey", "data_analysis"],
            "ml": ["machine_learning", "model", "training", "optimization", "algorithm"],
            "developer": ["code", "backend", "frontend", "api", "database", "implementation"],
            "writer": ["documentation", "report", "writing", "readme", "docs"],
            "data": ["data", "dataset", "etl", "processing", "annotation"],
            "review": ["review", "quality", "security", "bug", "issue"],
            "devops": ["deployment", "ci_cd", "infrastructure", "docker", "monitoring"],
            "pm": ["planning", "coordination", "task", "schedule", "milestone"],
        }
        return tag_map.get(agent_role, [])

    def is_finding_relevant_to_agent(self, finding: Finding, agent_role: str) -> bool:
        """
        判断一个发现是否与某Agent相关

        基于标签匹配
        """
        if not finding.relevant_tags:
            return True  # 没有标签，默认相关

        relevant_tags = self.get_agent_relevant_tags(agent_role)

        # 检查是否有交集
        for tag in finding.relevant_tags:
            if tag in relevant_tags:
                return True

        # 也检查agent名称是否在content中提到
        if agent_role.lower() in finding.content.lower():
            return True

        return False

    # ==================== 收集响应 ====================

    async def collect_responses(
        self,
        timeout: float = 120.0,
        min_responses: int = 1,
        check_interval: float = 2.0
    ) -> List[Finding]:
        """
        收集响应，直到超时或达到最小响应数

        MainAgent使用这个方法来收集各Agent的自主响应

        Args:
            timeout: 超时时间（秒）
            min_responses: 最小响应数
            check_interval: 检查间隔（秒）

        Returns:
            在此期间收集到的所有发现
        """
        self.observation_end_time = datetime.now().timestamp() + timeout
        initial_count = len(self.findings)

        while True:
            # 检查是否达到最小响应数
            if len(self.findings) - initial_count >= min_responses:
                break

            # 检查是否超时
            if datetime.now().timestamp() >= self.observation_end_time:
                break

            # 等待一段时间再检查
            await asyncio.sleep(check_interval)

        return self.findings[initial_count:]

    def get_new_findings_since(self, count: int) -> List[Finding]:
        """获取从某个索引之后的新发现"""
        return self.findings[count:]

    def get_all_findings(self) -> List[Finding]:
        """获取所有发现"""
        return self.findings.copy()

    def get_findings_by_agent(self, agent_role: str) -> List[Finding]:
        """获取特定Agent的所有发现"""
        return [f for f in self.findings if f.agent == agent_role]

    def get_findings_by_type(self, finding_type: FindingType) -> List[Finding]:
        """获取特定类型的所有发现"""
        return [f for f in self.findings if f.finding_type == finding_type]

    def get_pending_questions(self) -> List[PendingQuestion]:
        """获取所有待回答的问题"""
        return [q for q in self.pending_questions if not q.answered]

    # ==================== 任务管理 ====================

    async def create_task(self, task: Task) -> Task:
        """创建任务"""
        self.tasks[task.id] = task

        # 作为公告发布
        await self.post_finding(
            agent_role="system",
            content=f"新任务: {task.title}\n\n{task.description}",
            finding_type=FindingType.ANNOUNCEMENT,
            relevant_tags=[task.task_type, "task"]
        )

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: str) -> bool:
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            return True
        return False

    # ==================== 内部通知机制 ====================

    async def _notify_subscribers(self, finding: Finding):
        """通知所有相关的订阅者"""
        for agent_role, callback in self.subscribers.items():
            if self.is_finding_relevant_to_agent(finding, agent_role):
                try:
                    # 将事件放入队列
                    await self._event_queue.put((agent_role, finding))
                except Exception as e:
                    print(f"Error notifying subscriber {agent_role}: {e}")

    async def _notify_agent(self, agent_role: str, event: Dict[str, Any]):
        """直接通知特定Agent"""
        if agent_role in self.subscribers:
            try:
                # 创建一个人工finding来触发callback
                finding = Finding(
                    id=str(uuid.uuid4()),
                    agent="system",
                    finding_type=FindingType.ANNOUNCEMENT,
                    content=str(event),
                    metadata={"direct_notification": True}
                )
                await self._event_queue.put((agent_role, finding))
            except Exception as e:
                print(f"Error notifying agent {agent_role}: {e}")

    async def _broadcast(self, event: Dict[str, Any]):
        """广播事件给所有订阅者"""
        for agent_role in self.subscribers.keys():
            await self._notify_agent(agent_role, event)

    async def _event_listener(self):
        """事件监听器 - 处理异步通知"""
        while self._running:
            try:
                agent_role, finding = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                if agent_role in self.subscribers:
                    callback = self.subscribers[agent_role]
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(finding)
                        else:
                            callback(finding)
                    except Exception as e:
                        print(f"Error in subscriber callback for {agent_role}: {e}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error in event listener: {e}")

    # ==================== 状态查询 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取工作空间统计信息"""
        agent_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}

        for f in self.findings:
            agent_counts[f.agent] = agent_counts.get(f.agent, 0) + 1
            type_counts[f.finding_type.value] = type_counts.get(f.finding_type.value, 0) + 1

        return {
            "task_id": self.task_id,
            "total_findings": len(self.findings),
            "pending_questions": len([q for q in self.pending_questions if not q.answered]),
            "total_tasks": len(self.tasks),
            "active_tasks": len([t for t in self.tasks.values() if t.status == "in_progress"]),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == "completed"]),
            "findings_by_agent": agent_counts,
            "findings_by_type": type_counts,
            "subscriber_count": len(self.subscribers),
            "created_at": self.created_at
        }

    def __repr__(self) -> str:
        return f"SharedWorkspace(task_id={self.task_id}, findings={len(self.findings)}, subscribers={len(self.subscribers)})"


# ==================== 便捷函数 ====================

async def create_workspace_for_task(task_id: str, goal: str = "") -> SharedWorkspace:
    """为某个任务创建工作空间"""
    return await SharedWorkspace.create(task_id, goal)


def get_workspace(task_id: str) -> Optional[SharedWorkspace]:
    """获取工作空间"""
    return SharedWorkspace.get(task_id)


def list_workspaces() -> Dict[str, SharedWorkspace]:
    """列出所有工作空间"""
    return SharedWorkspace.list_all()
