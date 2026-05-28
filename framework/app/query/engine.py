"""
Query Engine
Main async generator-based query loop
"""
import asyncio
import json
import time
from typing import AsyncGenerator, List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass

from .config import QueryConfig, DEFAULT_QUERY_CONFIG
from .token_budget import TokenBudget, get_token_budget_manager
from .stop_hooks import StopContext, StopReason, get_stop_hook_manager
from ..tools.registry import tool_registry, ToolDefinition, ToolResult
from ..services.tools.orchestration import get_tool_orchestrator
from ..utils.logging import get_logger

logger = get_logger("query.engine")


@dataclass
class StreamEvent:
    """Represents a stream event"""
    type: str
    data: Dict[str, Any]


@dataclass
class Message:
    """Chat message"""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None  # for assistant messages
    tool_call_id: Optional[str] = None  # for tool messages


@dataclass
class ToolCall:
    """Represents a tool call"""
    name: str
    arguments: Dict[str, Any]
    id: str


@dataclass
class ToolResult:
    """Result of a tool execution"""
    tool_call_id: str
    name: str
    result: Any
    success: bool
    error: Optional[str] = None


class QueryEngine:
    """
    Main query engine using AsyncGenerator pattern.
    Streams events as they occur during query execution.
    """

    def __init__(
        self,
        workspace_path: str,
        config: Optional[QueryConfig] = None,
        llm_provider: Optional[Callable] = None,
        memory_dir: Optional[str] = None,
        sandbox_mode: str = "auto",
        allowed_permissions: Optional[List[str]] = None
    ):
        self._workspace_path = workspace_path
        self._config = config or DEFAULT_QUERY_CONFIG
        self._llm_provider = llm_provider
        self._turn_count = 0
        self._completed_tool_results: List[ToolResult] = []
        self._cancelled = False
        self._memory_dir = memory_dir
        self._sandbox_mode = sandbox_mode  # auto | host | docker
        self._allowed_permissions = allowed_permissions  # None = all allowed
        self._changed_files: set = set()  # Track files changed this turn

    async def query(
        self,
        messages: List[Message],
        system_prompt: str,
        tools: List[Dict[str, Any]],
        event_callback: Optional[Callable[[StreamEvent], Awaitable[None]]] = None,
        content_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Main query loop as an AsyncGenerator.

        Yields StreamEvent objects as they occur:
        - thinking_start: When thinking begins
        - content: When content is generated
        - tool_start: When a tool call starts
        - tool_result: When a tool call completes
        - thinking_complete: When thinking is done
        """
        logger.info(f"[QueryEngine] query() started")
        logger.debug(f"[QueryEngine] messages count: {len(messages)}, tools count: {len(tools)}")
        logger.debug(f"[QueryEngine] system_prompt length: {len(system_prompt)}")

        self._turn_count = 0
        self._completed_tool_results = []
        self._cancelled = False

        session_id = f"session_{int(time.time())}"
        budget_manager = get_token_budget_manager()
        budget = budget_manager.get_budget(session_id)

        hook_manager = get_stop_hook_manager()

        # Yield thinking start
        logger.info(f"[QueryEngine] Yielding thinking_start event")
        yield StreamEvent(
            type="thinking_start",
            data={"turn": self._turn_count + 1}
        )

        try:
            while self._turn_count < self._config.max_turns and not self._cancelled:
                self._turn_count += 1
                logger.info(f"[QueryEngine] Turn {self._turn_count} started")

                # Check stop hooks
                stop_context = StopContext(
                    turn_count=self._turn_count,
                    tool_results=[r.__dict__ for r in self._completed_tool_results],
                    token_usage=budget.used_tokens
                )
                stop_reason = await hook_manager.check_hooks(stop_context)
                if stop_reason:
                    logger.info(f"[QueryEngine] Stop reason: {stop_reason.value}")
                    yield StreamEvent(
                        type="thinking_complete",
                        data={
                            "reason": stop_reason.value,
                            "token_usage": budget.used_tokens,
                            "token_limit": budget.max_tokens
                        }
                    )
                    return

                # Build full context with system prompt
                # Inject memory system prompt
                from ..memory.prompt_builder import build_memory_system_prompt
                memory_prompt = build_memory_system_prompt(self._memory_dir)
                full_system_prompt = system_prompt + "\n\n" + memory_prompt

                # Temp directory hint for file operations
                import os as _os
                _temp_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), 'temp')
                full_system_prompt += (
                    f"\n\n## Working Directory\n"
                    f"Bash commands run in `{_temp_dir}`. "
                    f"All temporary files (scripts, downloads, data files) must be created here. "
                    f"This keeps the project root clean. Use the Write tool to create files in other project directories only when necessary."
                )

                # First-turn context enrichment
                if self._turn_count == 1:
                    user_msgs = [m for m in messages if m.role == 'user']
                    last_user = user_msgs[-1].content if user_msgs else ''

                    # Inject relevant past memories
                    try:
                        from ..memory.session_bridge import get_session_bridge
                        bridge = get_session_bridge()
                        relevant = bridge.find_relevant_memories(last_user, max_results=5)
                        if relevant:
                            lines = ["\n\n## Relevant Past Memories\n"]
                            for mem in relevant:
                                lines.append(f"- **[{mem.memory_type.value}] {mem.name}**: {mem.description}")
                                if mem.content:
                                    snippet = mem.content[:300].replace('\n', ' ')
                                    lines.append(f"  {snippet}")
                            lines.append("\nConsider these past memories when responding if applicable.")
                            full_system_prompt += "\n".join(lines)
                    except Exception:
                        pass

                    # Lightweight nudge: if user request is long, suggest task planning
                    if len(last_user) > 200:
                        full_system_prompt += (
                            "\n\n[HINT] This looks like a substantial request. "
                            "Consider using TaskCreate to break it into steps, "
                            "then TaskUpdate to track progress as you work."
                        )

                full_messages = [
                    Message(role="system", content=full_system_prompt),
                    *messages
                ]
                logger.debug(f"[QueryEngine] Full messages count: {len(full_messages)}")

                # Call LLM
                if self._llm_provider:
                    logger.info(f"[QueryEngine] Using custom LLM provider")
                    response = await self._llm_provider(
                        messages=full_messages,
                        tools=tools,
                        config=self._config
                    )
                else:
                    # Placeholder - would call actual LLM
                    logger.info(f"[QueryEngine] Calling _call_llm (placeholder)")
                    response = await self._call_llm(full_messages, tools)

                logger.debug(f"[QueryEngine] LLM response: {response}")

                # Update token budget from LLM response
                usage = response.get("usage", {})
                if usage:
                    budget.add_prompt_tokens(usage.get("prompt_tokens", 0))
                    budget.add_completion_tokens(usage.get("completion_tokens", 0))
                    logger.debug(
                        f"[QueryEngine] Tokens: +{usage.get('prompt_tokens', 0)}p +{usage.get('completion_tokens', 0)}c"
                        f" = {budget.used_tokens}/{budget.max_tokens}"
                    )

                # Process response — also collects tool results for message history
                tool_results_this_turn = []
                async for event in self._process_response(response, event_callback, content_callback):
                    logger.debug(f"[QueryEngine] Yielding event: {event.type}")
                    if event.type == "tool_result":
                        tool_results_this_turn.append(event.data)
                    yield event

                # Append assistant message + tool results to history for next turn
                assistant_content = response.get("content", "")
                raw_tool_calls = response.get("tool_calls", [])
                if assistant_content or raw_tool_calls:
                    messages.append(Message(
                        role="assistant",
                        content=assistant_content,
                        tool_calls=raw_tool_calls if raw_tool_calls else None
                    ))

                # Append each tool result as a tool message with tool_call_id
                for tr in tool_results_this_turn:
                    # Extract tool_call_id from the tool call data stored in _completed_tool_results
                    # The tool_call_id needs to match the assistant's tool_calls[].id
                    tool_call_id = tr.get("tool_call_id", "")
                    result_content = tr.get("result", "")
                    if isinstance(result_content, dict):
                        result_content = json.dumps(result_content, ensure_ascii=False)
                    messages.append(Message(
                        role="tool",
                        content=str(result_content),
                        tool_call_id=tool_call_id
                    ))

                # Commit changes for this turn (async, non-blocking)
                await self._commit_turn()

                # Check for more turns needed (tool calls handled in process_response)
                if not response.get("tool_calls"):
                    logger.info(f"[QueryEngine] No tool calls, yielding thinking_complete")
                    await self._commit_turn()  # Final commit before completion
                    yield StreamEvent(
                        type="thinking_complete",
                        data={
                            "turn": self._turn_count,
                            "token_usage": budget.used_tokens,
                            "token_limit": budget.max_tokens
                        }
                    )
                    return

        except asyncio.CancelledError:
            logger.info(f"[QueryEngine] Query cancelled")
            await self._commit_turn()  # Commit partial work before cancel
            yield StreamEvent(
                type="thinking_complete",
                data={
                    "reason": StopReason.CANCELLED.value,
                    "token_usage": budget.used_tokens,
                    "token_limit": budget.max_tokens
                }
            )
            raise
        except Exception as e:
            logger.error(f"[QueryEngine] Exception: {e}", exc_info=True)
            raise

    async def _call_llm(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call the LLM provider using LLMService from wolf_b.
        """
        from ..services.llm_service import LLMService
        from ..core.runtime_config import runtime_config

        # Convert Message objects to dict format
        msgs = []
        for m in messages:
            msg_dict = {"role": m.role, "content": m.content}
            if m.tool_calls:
                msg_dict["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            msgs.append(msg_dict)

        logger.info(f"[QueryEngine] Calling LLM via LLMService, provider: {runtime_config.current_provider}")

        try:
            llm_service = LLMService(provider=runtime_config.current_provider)
            result = await llm_service.complete(
                messages=msgs,
                tools=tools if tools else None,
                max_tokens=self._config.max_tokens
            )

            if result.get("success") or result.get("content"):
                usage = result.get("usage", {})
                return {
                    "content": result.get("content", ""),
                    "tool_calls": result.get("tool_calls", []),
                    "usage": usage
                }
            else:
                logger.error(f"[QueryEngine] LLM call failed: {result.get('error')}")
                return {
                    "content": f"LLM Error: {result.get('error', 'Unknown error')}",
                    "tool_calls": [],
                    "usage": {}
                }
        except Exception as e:
            logger.error(f"[QueryEngine] LLMService exception: {e}", exc_info=True)
            return {
                "content": f"Exception: {str(e)}",
                "tool_calls": []
            }

    async def _process_response(
        self,
        response: Dict[str, Any],
        event_callback: Optional[Callable[[StreamEvent], Awaitable[None]]],
        content_callback: Optional[Callable[[str], Awaitable[None]]]
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process LLM response and yield events"""

        # Handle content
        if "content" in response:
            content = response["content"]
            yield StreamEvent(type="content", data={"text": content})
            if content_callback:
                await content_callback(content)

        # Handle tool calls
        tool_calls = response.get("tool_calls", [])
        for tool_call_data in tool_calls:
            # Unwrap OpenAI standard format: {id, type, function: {name, arguments}}
            func = tool_call_data.get("function", {})
            name = func.get("name") or tool_call_data.get("name", "")
            raw_args = func.get("arguments") or tool_call_data.get("arguments", "{}")

            # arguments may be a JSON string (OpenAI format) or already a dict
            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}
            else:
                arguments = raw_args if isinstance(raw_args, dict) else {}

            tool_call = ToolCall(
                id=tool_call_data.get("id", ""),
                name=name,
                arguments=arguments
            )

            yield StreamEvent(
                type="tool_start",
                data={
                    "tool": tool_call.name,
                    "arguments": tool_call.arguments,
                    "tool_call_id": tool_call.id
                }
            )

            # Execute tool
            result = await self._execute_tool(tool_call)
            self._completed_tool_results.append(result)

            yield StreamEvent(
                type="tool_result",
                data={
                    "tool": result.name,
                    "tool_call_id": tool_call.id,
                    "result": result.result,
                    "success": result.success,
                    "error": result.error
                }
            )

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call using the tool orchestrator.
        """
        # Permission check
        tool_def = tool_registry.get(tool_call.name)
        allowed = getattr(self, '_allowed_permissions', None)
        if tool_def and allowed and tool_def.permission not in allowed:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                result=None,
                success=False,
                error=f"Permission denied: '{tool_call.name}' requires '{tool_def.permission}', allowed: {allowed}"
            )

        orchestrator = get_tool_orchestrator(tool_registry)

        tool_call_dict = {
            'id': tool_call.id,
            'name': tool_call.name,
            'input': tool_call.arguments
        }

        context = {
            'workspace_path': self._workspace_path,
            'turn_count': self._turn_count,
            'sandbox_mode': getattr(self, '_sandbox_mode', 'auto'),
            'allowed_permissions': allowed or ['read', 'write', 'shell', 'network', 'agent']
        }

        results = await orchestrator.execute_tools([tool_call_dict], context)

        # Track changed files for per-turn git commit
        if tool_def and tool_def.permission in ('write', 'shell'):
            self._track_changed_files(tool_call.arguments)

        if results and len(results) > 0:
            result = results[0]
            return ToolResult(
                tool_call_id=result.tool_call_id,
                name=result.name,
                result=result.result,
                success=result.success,
                error=result.error
            )

        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            result=None,
            success=False,
            error="No result returned"
        )

    def _track_changed_files(self, arguments: dict) -> None:
        """Track files that were potentially changed by this tool call"""
        paths = []
        for key in ('path', 'file_path', 'new_path'):
            v = arguments.get(key)
            if v and isinstance(v, str):
                paths.append(v)
        if paths:
            self._changed_files.update(paths)

    async def _commit_turn(self, tool_name: str = "") -> None:
        """Async git commit all files changed during this turn"""
        import os as _os
        try:
            # engine.py is at app/query/engine.py, go up 2 levels to wolf_b2/ (where .git is)
            project_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..'))
            summary = f"Turn {self._turn_count}: {tool_name}" if tool_name else f"Turn {self._turn_count}"

            if self._changed_files:
                # git add only the specific changed files (fast)
                cmd = ["git", "add", "--"] + list(self._changed_files)
                proc = await asyncio.create_subprocess_exec(
                    *cmd, cwd=project_root,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()
            else:
                # Fallback: git add -A but only in app/ dir (skip temp/, wolf_data/)
                cmd = ["git", "add", "app/"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, cwd=project_root,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()

            # Check if there's anything to commit
            status_proc = await asyncio.create_subprocess_exec(
                "git", "diff", "--cached", "--quiet",
                cwd=project_root
            )
            await status_proc.wait()
            if status_proc.returncode == 0:
                return  # Nothing to commit

            # Commit
            proc = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", summary,
                cwd=project_root,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await asyncio.wait_for(proc.wait(), timeout=10)
        except Exception:
            pass  # Non-critical, silent fail
        finally:
            self._changed_files.clear()

    async def cancel(self, reason: str = "user_requested") -> None:
        """Cancel the query — stops at next turn boundary and interrupts current LLM call"""
        self._cancelled = True
        self._cancel_reason = reason

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def cancel_reason(self) -> str:
        return getattr(self, '_cancel_reason', '')


async def create_query_engine(
    workspace_path: str,
    config: Optional[QueryConfig] = None
) -> QueryEngine:
    """Factory function to create a query engine"""
    return QueryEngine(
        workspace_path=workspace_path,
        config=config
    )