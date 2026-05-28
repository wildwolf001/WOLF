"""
Tool Orchestrator - 工具编排器
参考 cc-haha-main/src/services/tools/toolOrchestration.ts

实现工具并发控制:
- 读工具并发执行 (最多10个)
- 写工具串行执行
"""
import asyncio
import sys
from typing import List, Dict, Any, Optional
import uuid

from app.tools.registry import ToolRegistry, ToolDefinition, ToolResult

# 读工具最大并发数
MAX_CONCURRENT_READ_TOOLS = 10

class ToolOrchestrator:
    """
    工具编排器

    负责管理工具的并发执行:
    - 读工具可以并发执行 (最多MAX_CONCURRENT_READ_TOOLS个)
    - 写工具必须串行执行
    """

    def __init__(self, registry: ToolRegistry):
        self._registry = registry
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_READ_TOOLS)
        # 写工具锁
        self._write_lock = asyncio.Lock()
        # 正在执行的写工具
        self._running_writes: Dict[str, asyncio.Task] = {}

    async def execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[ToolResult]:
        """
        执行工具调用

        Args:
            tool_calls: 工具调用列表
            context: 执行上下文

        Returns:
            工具结果列表
        """
        if not tool_calls:
            return []

        # 按并发安全性分组
        batches = self._partition_tool_calls(tool_calls)

        results = []
        for batch in batches:
            if self._is_concurrency_safe(batch):
                # 并发执行读工具
                batch_results = await self._execute_batch_concurrent(batch, context)
            else:
                # 串行执行写工具
                batch_results = await self._execute_batch_serially(batch, context)
            results.extend(batch_results)

        return results

    def _partition_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        将工具调用分为批次

        规则:
        - 读工具放在一起 (可以并发)
        - 写工具单独一批
        """
        partitions = []
        current_partition = []

        for tool_call in tool_calls:
            tool = self._registry.get(tool_call.get('name', ''))
            if not tool:
                continue

            if tool.is_read_only:
                current_partition.append(tool_call)
            else:
                # 写工具单独一批
                if current_partition:
                    partitions.append(current_partition)
                    current_partition = []
                partitions.append([tool_call])

        if current_partition:
            partitions.append(current_partition)

        return partitions

    def _is_concurrency_safe(self, tool_calls: List[Dict[str, Any]]) -> bool:
        """检查批次是否可并发"""
        for tool_call in tool_calls:
            tool = self._registry.get(tool_call.get('name', ''))
            if not tool or not tool.is_read_only:
                return False
        return True

    async def _execute_batch_concurrent(
        self,
        tool_calls: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[ToolResult]:
        """并发执行批次 (读工具)"""
        async with self._semaphore:
            tasks = [
                self._execute_single(tool_call, context)
                for tool_call in tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    tool_name = tool_calls[i].get('name', 'unknown')
                    processed_results.append(ToolResult(
                        tool_call_id=tool_calls[i].get('id', str(uuid.uuid4())),
                        name=tool_name,
                        result=None,
                        success=False,
                        error=str(result)
                    ))
                else:
                    processed_results.append(result)

            return processed_results

    async def _execute_batch_serially(
        self,
        tool_calls: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[ToolResult]:
        """串行执行批次 (写工具)"""
        results = []
        async with self._write_lock:
            for tool_call in tool_calls:
                result = await self._execute_single(tool_call, context)
                results.append(result)
        return results

    async def _execute_single(
        self,
        tool_call: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ToolResult:
        """执行单个工具"""
        tool_name = tool_call.get('name', '')
        tool = self._registry.get(tool_name)

        tool_call_id = tool_call.get('id', str(uuid.uuid4()))

        if not tool:
            return ToolResult(
                tool_call_id=tool_call_id,
                name=tool_name,
                result=None,
                success=False,
                error=f"Tool not found: {tool_name}"
            )

        try:
            result = await tool.function(tool_call.get('input', {}), context)

            # 确保返回的是ToolResult
            if isinstance(result, ToolResult):
                return result
            else:
                # 如果返回的不是ToolResult，包装一下
                return ToolResult(
                    tool_call_id=tool_call_id,
                    name=tool_name,
                    result=result,
                    success=True
                )

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call_id,
                name=tool_name,
                result=None,
                success=False,
                error=str(e)
            )

    def get_running_count(self) -> int:
        """获取正在执行的工具数量"""
        return len(self._running_writes)

# 全局编排器实例
_tool_orchestrator: Optional[ToolOrchestrator] = None

def get_tool_orchestrator(registry: Optional[ToolRegistry] = None) -> ToolOrchestrator:
    """获取工具编排器实例"""
    global _tool_orchestrator
    if _tool_orchestrator is None and registry is not None:
        _tool_orchestrator = ToolOrchestrator(registry)
    return _tool_orchestrator