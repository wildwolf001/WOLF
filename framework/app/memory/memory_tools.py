"""
Memory Tools
实现记忆系统的操作工具
参考 cc-haha 的工具模式
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..tools.registry import tool_registry, ToolDefinition, ToolResult


MEMORY_READ_TOOL_NAME = "MemoryRead"
MEMORY_WRITE_TOOL_NAME = "MemoryWrite"
MEMORY_SEARCH_TOOL_NAME = "MemorySearch"
MEMORY_DELETE_TOOL_NAME = "MemoryDelete"
MEMORY_LIST_TOOL_NAME = "MemoryList"


class MemoryReadTool:
    name = MEMORY_READ_TOOL_NAME
    description = "Read memories from the memory system. Supports searching by query, type, or keyword."

    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query to find relevant memories"},
            "memory_type": {"type": "string", "enum": ["user", "feedback", "project", "reference"]},
            "keyword": {"type": "string", "description": "Keyword to search in memories"},
        },
    }

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        from ..memory.types import parse_memory_type
        from ..memory.search import get_memory_search_service

        tool_call_id = context.get('tool_use_id', '')

        try:
            search_service = get_memory_search_service()
            entries = []

            if arguments.get('memory_type'):
                memory_type = parse_memory_type(arguments['memory_type'])
                if memory_type:
                    entries = search_service.find_by_type(memory_type)
                else:
                    entries = search_service.get_all_memories()
            elif arguments.get('keyword'):
                results = search_service.find_by_keyword(arguments['keyword'])
                entries = [entry for _, entry in results]
            elif arguments.get('query'):
                entries = search_service.find_relevant(arguments['query'])
            else:
                entries = search_service.get_all_memories()

            if not entries:
                return ToolResult(tool_call_id=tool_call_id, name=self.name, result="No memories found", success=True)

            formatted = []
            for entry in entries:
                formatted.append(f"## {entry.name} [{entry.memory_type.value}]")
                formatted.append(f"Description: {entry.description}")
                formatted.append(f"Content: {entry.content}")
                formatted.append("")

            return ToolResult(tool_call_id=tool_call_id, name=self.name, result="\n".join(formatted), success=True)

        except Exception as e:
            return ToolResult(tool_call_id=tool_call_id, name=self.name, result="", success=False, error=str(e))


class MemoryWriteTool:
    name = MEMORY_WRITE_TOOL_NAME
    description = "Write a new memory to the memory system"

    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Memory name"},
            "memory_type": {"type": "string", "enum": ["user", "feedback", "project", "reference"]},
            "description": {"type": "string", "description": "One-line description for index (~150 chars)"},
            "content": {"type": "string", "description": "The memory content"},
        },
        "required": ["name", "memory_type", "description", "content"]
    }

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        from ..memory.types import parse_memory_type, MemoryEntry
        from ..memory.directory import get_memory_directory

        tool_call_id = context.get('tool_use_id', '')

        try:
            memory_type = parse_memory_type(arguments['memory_type'])
            if not memory_type:
                return ToolResult(tool_call_id=tool_call_id, name=self.name, result="", success=False, error=f"Invalid memory_type")

            entry = MemoryEntry(
                name=arguments['name'],
                description=arguments['description'],
                memory_type=memory_type,
                content=arguments['content']
            )

            memory_dir = get_memory_directory()
            filepath = memory_dir.write_memory(entry)

            return ToolResult(tool_call_id=tool_call_id, name=self.name, result=f"Memory saved to {filepath}", success=True)

        except Exception as e:
            return ToolResult(tool_call_id=tool_call_id, name=self.name, result="", success=False, error=str(e))


class MemorySearchTool:
    name = MEMORY_SEARCH_TOOL_NAME
    description = "Search memory file contents using pattern matching"

    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Search pattern"},
            "regex": {"type": "boolean", "default": False},
            "case_sensitive": {"type": "boolean", "default": True},
        },
        "required": ["pattern"]
    }

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        from ..memory.search import get_memory_search_service

        tool_call_id = context.get('tool_use_id', '')

        try:
            search_service = get_memory_search_service()
            results = search_service.search_content(
                pattern=arguments['pattern'],
                regex=arguments.get('regex', False),
                case_sensitive=arguments.get('case_sensitive', True)
            )

            if not results:
                return ToolResult(tool_call_id=tool_call_id, name=self.name, result="No matches found", success=True)

            formatted = []
            for filepath, line_no, line_content in results:
                formatted.append(f"{filepath}:{line_no}:{line_content}")

            return ToolResult(tool_call_id=tool_call_id, name=self.name, result="\n".join(formatted), success=True)

        except Exception as e:
            return ToolResult(tool_call_id=tool_call_id, name=self.name, result="", success=False, error=str(e))


class MemoryDeleteTool:
    name = MEMORY_DELETE_TOOL_NAME
    description = "Delete a memory by name"

    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the memory to delete"},
        },
        "required": ["name"]
    }

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        from ..memory.search import get_memory_search_service
        from ..memory.directory import get_memory_directory

        tool_call_id = context.get('tool_use_id', '')

        try:
            search_service = get_memory_search_service()
            entry = search_service.search_by_name(arguments['name'])

            if not entry:
                return ToolResult(tool_call_id=tool_call_id, name=self.name, result="", success=False, error="Memory not found")

            memory_dir = get_memory_directory()
            safe_name = arguments['name'].lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
            safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '_-')[:50]
            filename = f"{entry.memory_type.value}_{safe_name}.md"

            deleted = memory_dir.delete_memory(filename)

            if deleted:
                return ToolResult(tool_call_id=tool_call_id, name=self.name, result=f"Memory '{arguments['name']}' deleted", success=True)
            else:
                return ToolResult(tool_call_id=tool_call_id, name=self.name, result="", success=False, error="Failed to delete memory")

        except Exception as e:
            return ToolResult(tool_call_id=tool_call_id, name=self.name, result="", success=False, error=str(e))


class MemoryListTool:
    name = MEMORY_LIST_TOOL_NAME
    description = "List all memories with statistics"

    input_schema = {
        "type": "object",
        "properties": {
            "memory_type": {"type": "string", "enum": ["user", "feedback", "project", "reference"]},
            "limit": {"type": "integer", "default": 50},
        },
    }

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        from ..memory.search import get_memory_search_service
        from ..memory.types import parse_memory_type

        tool_call_id = context.get('tool_use_id', '')

        try:
            search_service = get_memory_search_service()
            stats = search_service.get_memory_stats()

            if arguments.get('memory_type'):
                memory_type = parse_memory_type(arguments['memory_type'])
                if memory_type:
                    entries = search_service.find_by_type(memory_type)
                else:
                    entries = search_service.get_all_memories()
            else:
                entries = search_service.get_all_memories()

            limit = arguments.get('limit', 50)
            entries = entries[:limit]

            lines = [
                f"Total memories: {stats['total']}",
                f"By type: {stats['by_type']}",
                "",
                "Memories:",
            ]

            for entry in entries:
                lines.append(f"- [{entry.name}] ({entry.memory_type.value}) - {entry.description}")

            return ToolResult(tool_call_id=tool_call_id, name=self.name, result="\n".join(lines), success=True)

        except Exception as e:
            return ToolResult(tool_call_id=tool_call_id, name=self.name, result="", success=False, error=str(e))


def register_memory_tools() -> None:
    """注册所有记忆相关工具到工具注册表"""
    read_tool = MemoryReadTool()
    write_tool = MemoryWriteTool()
    search_tool = MemorySearchTool()
    delete_tool = MemoryDeleteTool()
    list_tool = MemoryListTool()

    tool_registry.register(ToolDefinition(
        name=MEMORY_READ_TOOL_NAME,
        description=read_tool.description,
        input_schema=read_tool.input_schema,
        function=read_tool.execute,
        is_read_only=True
    ))

    tool_registry.register(ToolDefinition(
        name=MEMORY_WRITE_TOOL_NAME,
        description=write_tool.description,
        input_schema=write_tool.input_schema,
        function=write_tool.execute,
        is_read_only=False
    ))

    tool_registry.register(ToolDefinition(
        name=MEMORY_SEARCH_TOOL_NAME,
        description=search_tool.description,
        input_schema=search_tool.input_schema,
        function=search_tool.execute,
        is_read_only=True
    ))

    tool_registry.register(ToolDefinition(
        name=MEMORY_DELETE_TOOL_NAME,
        description=delete_tool.description,
        input_schema=delete_tool.input_schema,
        function=delete_tool.execute,
        is_read_only=False
    ))

    tool_registry.register(ToolDefinition(
        name=MEMORY_LIST_TOOL_NAME,
        description=list_tool.description,
        input_schema=list_tool.input_schema,
        function=list_tool.execute,
        is_read_only=True
    ))


__all__ = [
    'MEMORY_READ_TOOL_NAME',
    'MEMORY_WRITE_TOOL_NAME',
    'MEMORY_SEARCH_TOOL_NAME',
    'MEMORY_DELETE_TOOL_NAME',
    'MEMORY_LIST_TOOL_NAME',
    'register_memory_tools',
]