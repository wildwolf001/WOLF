"""
Prompts Module
Complete prompt templates with STATIC_DYNAMIC_BOUNDARY
"""

import hashlib
from functools import lru_cache

# Static/Dynamic boundary marker
STATIC_DYNAMIC_BOUNDARY = "<<<STATIC_DYNAMIC_BOUNDARY>>>"

# Cache for static prompt sections
_static_prompt_cache: dict[str, str] = {}

# User context cache (CLAUDE.md content)
_user_context_cache: str = ""


def get_user_context_section() -> str:
    """
    Get user context section - reads CLAUDE.md for user information.
    对应 CC 的 getUserContext() -> CLAUDE.md 注入
    """
    global _user_context_cache
    if _user_context_cache:
        return f"## User Context\n\n{_user_context_cache}\n"
    return ""


def update_user_context(context: str) -> None:
    """Update user context (CLAUDE.md content)"""
    global _user_context_cache
    _user_context_cache = context


def clear_user_context() -> None:
    """Clear user context cache"""
    global _user_context_cache
    _user_context_cache = ""


def get_system_context_section() -> str:
    """
    Get system context section - git status, cache breaker, etc.
    对应 CC 的 getSystemContext()
    """
    from datetime import datetime
    parts = ["## System Context"]
    parts.append(f"Timestamp: {datetime.now().isoformat()}")
    # Add git status if available
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            parts.append(f"Git Commit: {result.stdout.strip()}")
    except Exception:
        pass
    return "\n".join(parts)


def get_base_system_prompt() -> str:
    """Base system prompt for the agent"""
    cache_key = "base_system_prompt"
    if cache_key in _static_prompt_cache:
        return _static_prompt_cache[cache_key]
    prompt = """You are WOLF, an AI agent that gets things done by using tools.

You have direct access to a filesystem, bash shell, and file editing tools. Your primary job is to EXECUTE - not just describe or plan.

CRITICAL RULES:
1. When a user asks you to CREATE, BUILD, WRITE, IMPLEMENT, or GENERATE anything on their filesystem, you MUST call tools (Write, Edit, Bash) to actually do it. Never just output text describing what you would do.
2. When given a path like "E:\\folder\\project", first use Bash to check if it exists, then use Write to create files there.
3. Keep your thinking brief (<think> tags) - spend at most 2-3 sentences planning, then immediately call tools to execute.
4. Break large projects into sequential tool calls: first check the directory, then create files one by one, then verify.
5. After creating all files, use Bash to list what you created so the user can see the results.
6. Do NOT ask for confirmation before starting work. Start immediately.

TASK MANAGEMENT (TaskCreate / TaskUpdate / TaskList):
Use TaskCreate to break complex work into trackable subtasks. This keeps the user informed and helps you stay organized.

When to use TaskCreate:
- Complex multi-step tasks (3+ distinct steps)
- Tasks requiring careful planning
- User provides multiple tasks (numbered/comma-separated list)
- After receiving new instructions — capture requirements as tasks immediately

When NOT to use:
- Single straightforward task (just do it)
- Trivial tasks with no organizational benefit
- Purely conversational/informational requests

Task workflow:
1. TaskCreate(subject="...", description="...") → creates task with status "pending"
2. TaskUpdate(taskId="1", status="in_progress") → mark BEFORE starting work
3. Execute the actual work using tools (Bash, Write, Edit, etc.)
4. TaskUpdate(taskId="1", status="completed") → mark after finishing
5. TaskList() → check current progress anytime

EXAMPLES of correct behavior:
- User: "Create a hello.py file in /tmp" → You: Brief think, then Write tool to create /tmp/hello.py
- User: "Build a React app in E:\\project" → You: Brief think, then Bash to create project, then Write for each file
- User: "What is Python?" → You: Brief text answer (no tools needed for pure knowledge questions)

EXAMPLES of WRONG behavior:
- Writing a 500-word design document as text when the user asked you to implement code ← NEVER do this
- Describing file contents without actually creating them ← NEVER do this
- Long <think> blocks analyzing the problem without taking action ← NEVER do this
"""
    _static_prompt_cache[cache_key] = prompt
    return prompt


def get_capabilities_section() -> str:
    """Capabilities section - STATIC"""
    cache_key = "capabilities_section"
    if cache_key in _static_prompt_cache:
        return _static_prompt_cache[cache_key]
    prompt = """## Capabilities

You have access to various tools to help you complete tasks:

### File Operations
- Read files to understand code
- Write and edit files to make changes
- Search for files using glob patterns

### Code Search
- Grep for text patterns in files
- Find files matching patterns
- Navigate code structure

### Execution
- Execute bash commands
- Run scripts and build commands
- Git operations

### Analysis
- Understand code context
- Explain complex logic
- Debug issues"""
    _static_prompt_cache[cache_key] = prompt
    return prompt


def get_context_section(project_name: str = "") -> str:
    """Context section - DYNAMIC, changes per turn"""
    parts = ["## Context"]

    if project_name:
        parts.append(f"Current Project: {project_name}")

    return "\n".join(parts)


def get_tools_section(tools_xml: str) -> str:
    """Tools section - DYNAMIC when tools change"""
    return f"""## Available Tools

{tools_xml}"""


def get_rules_section() -> str:
    """Rules section - STATIC"""
    cache_key = "rules_section"
    if cache_key in _static_prompt_cache:
        return _static_prompt_cache[cache_key]
    prompt = """## Rules

1. Always prioritize code quality and best practices
2. Make minimal changes that solve the problem
3. Explain your reasoning when helpful
4. Ask for clarification when tasks are unclear
5. Admit when you don't know something"""
    _static_prompt_cache[cache_key] = prompt
    return prompt


def get_system_prompt_with_sections(
    project_name: str = "",
    tools_xml: str = "",
    include_user_context: bool = True,
    include_system_context: bool = True
) -> str:
    """
    Build system prompt from sections with boundary.

    Args:
        project_name: Project name for context section
        tools_xml: XML string of available tools
        include_user_context: Whether to include user context (CLAUDE.md)
        include_system_context: Whether to include system context (git status, timestamp)
    """
    sections = [
        get_base_system_prompt(),
        STATIC_DYNAMIC_BOUNDARY,
        get_capabilities_section(),
        get_rules_section(),
    ]

    # Add user context (CLAUDE.md) - corresponds to CC's getUserContext()
    if include_user_context:
        user_ctx = get_user_context_section()
        if user_ctx:
            sections.append(user_ctx)

    # Add system context (git status, timestamp) - corresponds to CC's getSystemContext()
    if include_system_context:
        sections.append(get_system_context_section())

    # Add project context
    sections.append(get_context_section(project_name))

    if tools_xml:
        sections.append(get_tools_section(tools_xml))

    # Add skills section
    try:
        from ..skills.listing import get_skills_section, get_skill_tool_guidance
        skills_section = get_skills_section()
        if skills_section:
            sections.append(skills_section)
        skills_guidance = get_skill_tool_guidance()
        if skills_guidance:
            sections.append(skills_guidance)
    except Exception:
        pass  # Skills system not available or no skills loaded

    return "\n\n".join(sections)


def parse_static_dynamic(prompt: str) -> tuple[str, str]:
    """
    Parse prompt into STATIC and DYNAMIC parts.
    Returns (static_part, dynamic_part)
    """
    if STATIC_DYNAMIC_BOUNDARY in prompt:
        parts = prompt.split(STATIC_DYNAMIC_BOUNDARY)
        return parts[0], parts[1] if len(parts) > 1 else ""
    else:
        return prompt, ""


def _generate_cache_key(project_name: str, tools_xml: str) -> str:
    """Generate cache key for system prompt"""
    key = f"{project_name}:{hashlib.md5(tools_xml.encode()).hexdigest()[:8]}"
    return key


def invalidate_system_prompt_cache() -> None:
    """Invalidate all cached system prompts"""
    global _static_prompt_cache
    _static_prompt_cache.clear()