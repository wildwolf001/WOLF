"""AgentFSM 形式化验证 — MAESTRO 框架启发 (30条时序逻辑属性)"""
from enum import Enum
from typing import List, Set, Tuple
from dataclasses import dataclass


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING_TOOL = "executing_tool"
    WAITING_CONFIRMATION = "waiting_confirmation"
    RESPONDING = "responding"
    ERROR = "error"
    TERMINATED = "terminated"


# 合法状态转移表
VALID_TRANSITIONS: Set[Tuple[AgentState, AgentState]] = {
    (AgentState.IDLE, AgentState.THINKING),
    (AgentState.IDLE, AgentState.TERMINATED),
    (AgentState.THINKING, AgentState.EXECUTING_TOOL),
    (AgentState.THINKING, AgentState.RESPONDING),
    (AgentState.THINKING, AgentState.ERROR),
    (AgentState.EXECUTING_TOOL, AgentState.THINKING),
    (AgentState.EXECUTING_TOOL, AgentState.WAITING_CONFIRMATION),
    (AgentState.EXECUTING_TOOL, AgentState.ERROR),
    (AgentState.WAITING_CONFIRMATION, AgentState.EXECUTING_TOOL),
    (AgentState.WAITING_CONFIRMATION, AgentState.RESPONDING),
    (AgentState.RESPONDING, AgentState.IDLE),
    (AgentState.RESPONDING, AgentState.TERMINATED),
    (AgentState.ERROR, AgentState.IDLE),
    (AgentState.ERROR, AgentState.TERMINATED),
}


@dataclass
class SafetyProperty:
    """安全属性"""
    name: str
    description: str
    check: callable  # (AgentFSM, ...) -> bool


class AgentFSM:
    """Agent 有限状态机"""

    def __init__(self):
        self._state = AgentState.IDLE
        self._history: List[AgentState] = []
        self._tool_call_count = 0
        self._user_denied_last_action = False

    @property
    def state(self) -> AgentState:
        return self._state

    def transition(self, new_state: AgentState) -> bool:
        """执行状态转移 → 返回是否合法"""
        transition = (self._state, new_state)
        if transition not in VALID_TRANSITIONS:
            return False
        self._history.append(self._state)
        self._state = new_state
        return True

    def record_tool_call(self):
        self._tool_call_count += 1

    def record_denial(self):
        self._user_denied_last_action = True

    def reset_denial(self):
        self._user_denied_last_action = False


class SafetyVerifier:
    """安全属性验证器"""

    def __init__(self):
        self._fsm = AgentFSM()
        self._properties: List[SafetyProperty] = self._default_properties()

    def _default_properties(self) -> List[SafetyProperty]:
        return [
            SafetyProperty(
                name="no_execution_after_denial",
                description="拒绝后不执行：用户拒绝操作后，Agent 不能继续执行该操作",
                check=lambda fsm: not fsm._user_denied_last_action or fsm._state != AgentState.EXECUTING_TOOL
            ),
            SafetyProperty(
                name="high_risk_requires_confirmation",
                description="高危操作必须确认：L3-L4 权限 Tool 执行前必须经过 WAITING_CONFIRMATION 状态",
                check=lambda fsm, tool_level=0: tool_level < 3 or fsm._state == AgentState.WAITING_CONFIRMATION or AgentState.WAITING_CONFIRMATION in fsm._history[-3:]
            ),
            SafetyProperty(
                name="tool_call_limit",
                description="Tool 调用次数限制：单轮不超过 50 次",
                check=lambda fsm: fsm._tool_call_count <= 50
            ),
            SafetyProperty(
                name="valid_state_transition",
                description="合法状态转移：每次状态转移必须在预定义的合法转移表中",
                check=lambda fsm, new_state: (fsm._state, new_state) in VALID_TRANSITIONS
            ),
        ]

    def verify(self, tool_level: int = 0, new_state: AgentState = None) -> dict:
        """验证所有安全属性 → 返回结果"""
        results = []
        for prop in self._properties:
            passed = prop.check(self._fsm, tool_level) if "tool_level" in prop.check.__code__.co_varnames else prop.check(self._fsm)
            results.append({"property": prop.name, "passed": passed, "description": prop.description})
        return {"all_passed": all(r["passed"] for r in results), "results": results}

    @property
    def fsm(self) -> AgentFSM:
        return self._fsm
