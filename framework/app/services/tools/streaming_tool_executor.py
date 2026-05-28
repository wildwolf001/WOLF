"""
Streaming Tool Executor
Executes tools in parallel for read-only, serial for write operations
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum


class ToolType(Enum):
    """Tool execution type"""
    READONLY = "readonly"  # Can run in parallel
    WRITE = "write"  # Must run serial to avoid conflicts
    MIXED = "mixed"  # Has both read and write operations


@dataclass
class ToolCall:
    """Represents a tool call"""
    id: str
    name: str
    arguments: Dict[str, Any]
    tool_type: ToolType = ToolType.READONLY


@dataclass
class ToolExecutionResult:
    """Result of a tool execution"""
    tool_call_id: str
    name: str
    result: Any
    success: bool
    error: Optional[str] = None
    execution_time: float = 0.0


class StreamingToolExecutor:
    """
    Executes tools with parallel execution for read-only operations
    and serial execution for write operations.
    """

    # Standard tool classifications
    READONLY_TOOLS = {"read", "list", "glob", "grep", "exists", "file_read", "file_list", "file_glob", "file_grep", "file_exists"}
    WRITE_TOOLS = {"write", "edit", "bash", "file_write", "file_edit", "execute"}

    def __init__(
        self,
        tool_executor: Optional[Callable] = None,
        max_parallel: int = 5
    ):
        self._tool_executor = tool_executor or self._default_executor
        self._max_parallel = max_parallel

    def classify_tool(self, tool_name: str) -> ToolType:
        """Classify a tool by type"""
        if tool_name in self.READONLY_TOOLS:
            return ToolType.READONLY
        elif tool_name in self.WRITE_TOOLS:
            return ToolType.WRITE
        else:
            return ToolType.MIXED

    async def _default_executor(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Default tool executor placeholder"""
        # Simulate execution
        await asyncio.sleep(0.1)
        return {"status": "ok", "tool": tool_name, "args": arguments}

    async def execute_single(
        self,
        tool_call: ToolCall
    ) -> ToolExecutionResult:
        """Execute a single tool call"""
        import time
        start = time.time()

        try:
            result = await self._tool_executor(tool_call.name, tool_call.arguments)
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                result=result,
                success=True,
                execution_time=time.time() - start
            )
        except Exception as e:
            return ToolExecutionResult(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                result=None,
                success=False,
                error=str(e),
                execution_time=time.time() - start
            )

    async def execute_parallel(
        self,
        tool_calls: List[ToolCall]
    ) -> List[ToolExecutionResult]:
        """
        Execute tool calls in parallel for read-only tools.
        Returns results in the same order as input.
        """
        readonly_calls = [tc for tc in tool_calls if tc.tool_type == ToolType.READONLY]

        if not readonly_calls:
            return []

        # Execute readonly in parallel
        tasks = [self.execute_single(tc) for tc in readonly_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ToolExecutionResult(
                    tool_call_id=readonly_calls[i].id,
                    name=readonly_calls[i].name,
                    result=None,
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)

        return final_results

    async def execute_serial(
        self,
        tool_calls: List[ToolCall]
    ) -> List[ToolExecutionResult]:
        """
        Execute tool calls serially (for write operations).
        """
        results = []
        for tc in tool_calls:
            result = await self.execute_single(tc)
            results.append(result)
        return results

    async def execute(
        self,
        tool_calls: List[ToolCall]
    ) -> List[ToolExecutionResult]:
        """
        Execute tool calls with appropriate strategy.
        Readonly tools run in parallel, write tools run serial.
        """
        readonly = [tc for tc in tool_calls if self.classify_tool(tc.name) == ToolType.READONLY]
        write = [tc for tc in tool_calls if self.classify_tool(tc.name) == ToolType.WRITE]

        # Execute readonly in parallel
        readonly_results = await self.execute_parallel(readonly) if readonly else []

        # Execute writes serial
        write_results = await self.execute_serial(write) if write else []

        # Combine and return in original order
        results_by_id = {}
        for result in readonly_results + write_results:
            results_by_id[result.tool_call_id] = result

        return [results_by_id[tc.id] for tc in tool_calls]

    async def execute_streaming(
        self,
        tool_calls: List[ToolCall]
    ) -> AsyncGenerator[ToolExecutionResult, None]:
        """
        Execute tool calls and yield results as they complete.
        """
        readonly = [tc for tc in tool_calls if self.classify_tool(tc.name) == ToolType.READONLY]
        write = [tc for tc in tool_calls if self.classify_tool(tc.name) == ToolType.WRITE]

        # Queue for parallel execution
        if readonly:
            tasks = [self.execute_single(tc) for tc in readonly]
            for coro in asyncio.as_completed(tasks):
                result = await coro
                yield result

        # Execute writes serial
        for tc in write:
            result = await self.execute_single(tc)
            yield result


# Global executor instance
_tool_executor: Optional[StreamingToolExecutor] = None


def get_tool_executor() -> StreamingToolExecutor:
    """Get the global tool executor"""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = StreamingToolExecutor()
    return _tool_executor