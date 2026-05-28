"""
条件化 Prompt 组装 — 对标 CC getSessionSpecificGuidanceSection()
根据 Agent 当前能力 (启用了哪些 Tool / 加载了哪些 Skill / 会话模式) 动态注入 Prompt
"""
from typing import List, Set
from .layers import PromptAssembler, PromptLayer
from .core.schemas import LayerType, CacheScope, SessionMode


class ConditionalAssembler:
    """条件化 Prompt 组装器 — 对标 CC prompts.ts 的条件注入逻辑"""

    def __init__(self):
        self._assembler = PromptAssembler()

    def build(
        self,
        enabled_tools: Set[str],
        active_skills: List[str] = None,
        session_mode: SessionMode = SessionMode.DEFAULT,
        has_agent_tool: bool = False,
        has_skill_tool: bool = False,
        is_repl_mode: bool = False,
    ) -> str:
        """根据 Agent 能力动态构建 System Prompt"""
        active_skills = active_skills or []

        # ── Static 层 (Global cache — 跨会话复用) ──
        self._assembler.add_layer(PromptLayer(
            name="base_identity",
            layer_type=LayerType.ROLE,
            compute=_base_identity,
            cache_scope=CacheScope.GLOBAL
        ))
        self._assembler.add_layer(PromptLayer(
            name="doing_tasks",
            layer_type=LayerType.RULES,
            compute=_doing_tasks_rules,
            cache_scope=CacheScope.GLOBAL
        ))
        self._assembler.add_layer(PromptLayer(
            name="actions_risk",
            layer_type=LayerType.RULES,
            compute=_actions_risk_rules,
            cache_scope=CacheScope.GLOBAL
        ))
        self._assembler.add_layer(PromptLayer(
            name="using_tools",
            layer_type=LayerType.RULES,
            compute=lambda: _using_tools_rules(enabled_tools),
            cache_scope=CacheScope.GLOBAL
        ))

        # ── Conditional 层 (根据能力条件注入) ──
        if has_skill_tool and active_skills:
            self._assembler.add_layer(PromptLayer(
                name="skills_guidance",
                layer_type=LayerType.CONTEXT,
                compute=lambda: _skills_guidance(active_skills),
                cache_scope=CacheScope.SESSION,
                condition=lambda: bool(active_skills)
            ))

        if has_agent_tool:
            self._assembler.add_layer(PromptLayer(
                name="agent_tool_guidance",
                layer_type=LayerType.CONTEXT,
                compute=_agent_tool_guidance,
                cache_scope=CacheScope.SESSION,
                condition=lambda: has_agent_tool
            ))

        # ── Dynamic 层 (每轮重新计算) ──
        if is_repl_mode:
            self._assembler.add_layer(PromptLayer(
                name="repl_mode_guidance",
                layer_type=LayerType.CONTEXT,
                compute=_repl_mode_guidance,
                cache_scope=CacheScope.DYNAMIC
            ))
        else:
            self._assembler.add_layer(PromptLayer(
                name="default_mode_guidance",
                layer_type=LayerType.CONTEXT,
                compute=_default_mode_guidance,
                cache_scope=CacheScope.SESSION
            ))

        return self._assembler.assemble()


# ── Prompt 内容函数 ──

def _base_identity() -> str:
    return """# System
You are WOLF, an AI agent that helps users with software engineering tasks.
Use the instructions below and the tools available to you to assist the user.

IMPORTANT: You must NEVER generate or guess URLs for the user. You may use URLs provided by the user in their messages or local files."""

def _doing_tasks_rules() -> str:
    return """# Doing tasks
- The user will primarily request you to perform software engineering tasks.
- You are highly capable and often allow users to complete ambitious tasks.
- In general, do not propose changes to code you haven't read.
- Do not create files unless they're absolutely necessary.
- Avoid giving time estimates.
- If an approach fails, diagnose why before switching tactics.
- Prioritize writing safe, secure, and correct code.
- Don't add features, refactor code, or make "improvements" beyond what was asked.
- Don't add error handling for scenarios that can't happen.
- Don't create helpers for one-time operations."""

def _actions_risk_rules() -> str:
    return """# Executing actions with care
Carefully consider the reversibility and blast radius of actions. For destructive operations
(deleting files, force-pushing, dropping tables) check with the user before proceeding.
When in doubt, ask before acting. Measure twice, cut once."""

def _using_tools_rules(enabled_tools: Set[str]) -> str:
    tool_list = ", ".join(sorted(enabled_tools)) if enabled_tools else "standard tools"
    return f"""# Using your tools
Available dedicated tools: {tool_list}
- Do NOT use Bash when a relevant dedicated tool is provided.
- Read for cat/head/tail, Edit for sed/awk, Write for echo/cat redirect.
- Reserve Bash for system commands that require shell execution.
- Call multiple tools in parallel when there are no dependencies.
- Break complex tasks with TaskCreate."""

def _skills_guidance(active_skills: List[str]) -> str:
    skill_list = "\n".join(f"  - /{s}" for s in active_skills)
    return f"""# Session-specific guidance
Available skills (use the Skill tool to execute):
{skill_list}

IMPORTANT: Only use Skill for skills listed above - do not guess built-in CLI commands."""

def _agent_tool_guidance() -> str:
    return """# Using sub-agents
Use the Agent tool with specialized sub-agents when the task matches the agent's description.
Sub-agents are valuable for parallelizing independent queries or protecting the main context
window from excessive results. Avoid duplicating work that sub-agents are already doing."""

def _repl_mode_guidance() -> str:
    return """# REPL Mode
You are in REPL mode. Use the REPL tool for interactive code execution."""

def _default_mode_guidance() -> str:
    return """# Default Mode
Execute directly. Use tools to read, edit, and create files as needed."""
