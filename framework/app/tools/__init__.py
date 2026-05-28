"""
Tools Module
Provides tool registry and implementations
"""
from app.tools.registry import ToolRegistry, ToolDefinition, ToolResult, tool_registry
from app.tools.agent.definitions import (
    AgentType, AgentDefinition, AgentToolInput, AgentToolResult,
    BUILT_IN_AGENTS, get_builtin_agent, get_all_builtin_agents
)
from app.tools.agent.tool import AgentTool, register_agent_tool

__all__ = [
    'ToolRegistry', 'ToolDefinition', 'ToolResult', 'tool_registry',
    'AgentType', 'AgentDefinition', 'AgentToolInput', 'AgentToolResult',
    'BUILT_IN_AGENTS', 'get_builtin_agent', 'get_all_builtin_agents',
    'AgentTool', 'register_agent_tool',
    'register_skill_tool',
]

def register_all_tools(temp_dir: str = None):
    """Register all built-in tools with the registry"""
    import os
    # Register agent tool
    register_agent_tool()

    # Import tool implementations
    from app.tools.definitions.bash import BashTool
    from app.tools.definitions.file_read import FileReadTool
    from app.tools.definitions.file_edit import FileEditTool
    from app.tools.definitions.file_write import FileWriteTool
    from app.tools.definitions.glob import GlobTool
    from app.tools.definitions.grep import GrepTool

    # Resolve temp directory
    _temp_dir = temp_dir
    if not _temp_dir:
        _temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp')
    os.makedirs(_temp_dir, exist_ok=True)

    # Register BashTool — runs in temp/ to avoid cluttering project root
    bash_tool = BashTool(working_dir=_temp_dir)
    _sandbox_mode = os.getenv('WOLF_SANDBOX_MODE', 'auto').lower()

    async def _bash_sandbox_wrapper(args, ctx):
        """Bash wrapper with sandbox awareness"""
        command = args.get('command', '')
        timeout = args.get('timeout', 60)
        environment = args.get('environment')

        # Check context for sandbox override
        effective_mode = ctx.get('sandbox_mode', _sandbox_mode)

        if effective_mode in ('auto', 'docker'):
            try:
                from ..sandbox import SandboxExecutor
                project_root = os.path.dirname(_temp_dir)
                sandbox = SandboxExecutor(
                    mode=effective_mode,
                    project_root=project_root,
                    temp_dir=_temp_dir
                )
                if sandbox.mode == 'docker':
                    result = await sandbox.run(command, timeout=timeout, env=environment)
                    return ToolResult(
                        tool_call_id=ctx.get('tool_use_id', ''),
                        name='Bash',
                        result={
                            'success': result.success,
                            'stdout': result.stdout,
                            'stderr': result.stderr,
                            'returncode': result.exit_code,
                            'sandbox': 'docker'
                        },
                        success=result.success
                    )
            except Exception:
                pass  # fall through to host mode

        # Host mode or sandbox unavailable
        try:
            raw = await bash_tool.execute(command, timeout=timeout, environment=environment)
            raw['sandbox'] = 'host'
            return ToolResult(
                tool_call_id=ctx.get('tool_use_id', ''),
                name='Bash',
                result=raw,
                success=raw.get('success', False)
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=ctx.get('tool_use_id', ''),
                name='Bash',
                result={'success': False, 'error': str(e), 'stdout': '', 'stderr': '', 'returncode': -1},
                success=False,
                error=str(e)
            )

    tool_registry.register(ToolDefinition(
        name='Bash',
        description=f'Execute shell commands. Working directory: {_temp_dir}. Sandbox: {_sandbox_mode}.',
        input_schema=bash_tool.get_schema()['input_schema'],
        function=_bash_sandbox_wrapper,
        is_read_only=False,
        permission='shell'
    ))

    # Register FileReadTool
    read_tool = FileReadTool()
    tool_registry.register(ToolDefinition(
        name='Read',
        description='Read file contents',
        input_schema=read_tool.get_schema()['input_schema'],
        function=lambda args, ctx: read_tool.execute(**args),
        is_read_only=True,
        permission='read'
    ))

    # Register FileEditTool
    edit_tool = FileEditTool()
    tool_registry.register(ToolDefinition(
        name='Edit',
        description='Edit file contents',
        input_schema=edit_tool.get_schema()['input_schema'],
        function=lambda args, ctx: edit_tool.execute(**args),
        is_read_only=False,
        permission='write'
    ))

    # Register FileWriteTool
    write_tool = FileWriteTool()
    tool_registry.register(ToolDefinition(
        name='Write',
        description='Write content to a file',
        input_schema=write_tool.get_schema()['input_schema'],
        function=lambda args, ctx: write_tool.execute(**args),
        is_read_only=False,
        permission='write'
    ))

    # Register GlobTool
    glob_tool = GlobTool()
    tool_registry.register(ToolDefinition(
        name='Glob',
        description='Search for files by pattern',
        input_schema=glob_tool.get_schema()['input_schema'],
        function=lambda args, ctx: glob_tool.execute(**args),
        is_read_only=True,
        permission='read'
    ))

    # Register GrepTool
    grep_tool = GrepTool()
    tool_registry.register(ToolDefinition(
        name='Grep',
        description='Search file contents',
        input_schema=grep_tool.get_schema()['input_schema'],
        function=lambda args, ctx: grep_tool.execute(**args),
        is_read_only=True,
        permission='read'
    ))

    # Register Skill tool (lazy import to avoid circular dependency)
    from app.skills.tool import register_skill_tool
    register_skill_tool()

    # Register Task tools — TaskCreate, TaskUpdate, TaskList
    from app.tools.definitions.task import (
        task_create, TASK_CREATE_SCHEMA,
        task_update, TASK_UPDATE_SCHEMA,
        task_list, TASK_LIST_SCHEMA,
    )
    tool_registry.register(ToolDefinition(
        name='TaskCreate',
        description='Create a new task to track progress. Use for complex multi-step tasks.',
        input_schema=TASK_CREATE_SCHEMA,
        function=task_create,
        is_read_only=False,
        permission='write'
    ))
    tool_registry.register(ToolDefinition(
        name='TaskUpdate',
        description='Update a task (change status, set owner, add dependencies). Use to mark tasks as in_progress or completed.',
        input_schema=TASK_UPDATE_SCHEMA,
        function=task_update,
        is_read_only=False,
        permission='write'
    ))
    tool_registry.register(ToolDefinition(
        name='TaskList',
        description='List all tasks with their statuses. Use to see current progress.',
        input_schema=TASK_LIST_SCHEMA,
        function=task_list,
        is_read_only=True,
        permission='read'
    ))