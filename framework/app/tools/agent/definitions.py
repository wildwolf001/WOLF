"""
Agent Definitions - Agent定义
参考 cc-haha-main/src/tools/AgentTool/AgentTool.tsx
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import asyncio

class AgentType(str, Enum):
    """Agent类型"""
    GENERAL_PURPOSE = "general-purpose"
    PLAN = "plan"
    EXPLORE = "explore"
    VERIFICATION = "verification"

@dataclass
class AgentDefinition:
    """
    Agent定义
    对应 CC 的 AgentDefinition
    """
    agent_type: str
    description: str
    tools: List[str] = field(default_factory=lambda: ["*"])
    source: str = "built-in"
    base_dir: str = "built-in"
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    max_turns: Optional[int] = None
    mcp_servers: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    memory: Optional[str] = None
    background: bool = False
    isolation: Optional[str] = None
    permission_mode: Optional[str] = None
    effort: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'agent_type': self.agent_type,
            'description': self.description,
            'tools': self.tools,
            'source': self.source,
            'model': self.model,
            'max_turns': self.max_turns,
        }

@dataclass
class AgentToolInput:
    """Agent工具输入"""
    description: str
    prompt: str
    subagent_type: Optional[str] = None
    model: Optional[str] = None
    run_in_background: bool = False
    name: Optional[str] = None
    team_name: Optional[str] = None
    mode: Optional[str] = None
    isolation: Optional[str] = None
    cwd: Optional[str] = None

@dataclass
class AgentToolResult:
    """Agent工具结果"""
    status: str  # "completed" or "async_launched"
    result: Optional[str] = None
    agent_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class AgentProgress:
    """Agent进度"""
    tool_use_count: int = 0
    token_count: int = 0
    last_activity: Optional[Dict[str, Any]] = None
    recent_activities: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None

# 内置Agent定义
BUILT_IN_AGENTS: Dict[str, AgentDefinition] = {}

def _init_builtin_agents():
    """初始化内置Agent"""
    global BUILT_IN_AGENTS
    
    BUILT_IN_AGENTS = {
        AgentType.GENERAL_PURPOSE: AgentDefinition(
            agent_type=AgentType.GENERAL_PURPOSE,
            description="General-purpose agent for researching complex questions, searching for code, and executing multi-step tasks.",
            tools=["*"],
            source="built-in",
            system_prompt="""You are an agent for WOLF. Complete the task fully.

Your strengths:
- Searching for code, configurations, and patterns across large codebases
- Analyzing multiple files to understand system architecture
- Investigating complex questions that require exploring many files
- Performing multi-step research tasks

Guidelines:
- For file searches: search broadly when you don't know where something lives
- For analysis: Start broad and narrow down
- Be thorough: Check multiple locations, consider different naming conventions
- NEVER create files unless they're absolutely necessary for achieving your goal
- NEVER proactively create documentation files (*.md) or README files"""
        ),
        AgentType.PLAN: AgentDefinition(
            agent_type=AgentType.PLAN,
            description="Plan mode for complex tasks - creates a detailed plan before execution",
            tools=["*"],
            source="built-in",
            system_prompt="""You are a planning agent. Your job is to create a detailed plan before executing any task.

Steps:
1. Understand the task requirements
2. Identify the key components needed
3. Break down into manageable steps
4. Consider potential issues and edge cases
5. Present the plan for review

Do not execute the task - only create the plan."""
        ),
        AgentType.EXPLORE: AgentDefinition(
            agent_type=AgentType.EXPLORE,
            description="Explore and research agent for investigating codebases",
            tools=["*"],
            source="built-in",
            system_prompt="""You are an exploration agent. Your job is to thoroughly explore and research.

Guidelines:
- Search broadly across the codebase
- Look for patterns and relationships
- Document findings comprehensively
- Consider multiple perspectives
- Be curious and dig deeper"""
        ),
        AgentType.VERIFICATION: AgentDefinition(
            agent_type=AgentType.VERIFICATION,
            description="Verification agent for checking and validating results",
            tools=["*"],
            source="built-in",
            isolation="auto",  # 优先 Docker，不可用时降级 host
            system_prompt="""You are a verification agent. Your job is to verify results and find issues.

Guidelines:
- Run the actual code to verify it works
- Check work thoroughly — don't just read, execute
- Look for edge cases and corner cases
- Verify assumptions by running tests
- If tests don't exist, create minimal test scripts and run them
- Install dependencies if needed (pip install / npm install)
- Report issues clearly with specific file paths and line numbers
- Be critical — if something doesn't work, say so directly

Verification steps:
1. Read the implementation files to understand what was built
2. Identify the entry point and how to test it
3. Run the code with sample inputs
4. If it fails, diagnose why and report the exact error
5. Suggest fixes if possible"""
        ),
    }

_init_builtin_agents()

def get_builtin_agent(agent_type: str) -> Optional[AgentDefinition]:
    """获取内置Agent"""
    return BUILT_IN_AGENTS.get(agent_type)

def get_all_builtin_agents() -> List[AgentDefinition]:
    """获取所有内置Agent"""
    return list(BUILT_IN_AGENTS.values())

# One-shot agents that run once and return a report
ONE_SHOT_AGENT_TYPES = {"Explore", "Plan"}
