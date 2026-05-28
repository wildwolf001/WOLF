"""
Tools Route
"""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from ..models import ToolCallRequest

router = APIRouter()


@router.get("/tools")
async def list_tools() -> dict:
    """List all available tools"""
    from ...tools.definitions import (
        bash, file_read, file_write, file_edit,
        glob, grep, web_search, web_fetch, task
    )

    tools = [
        {
            "name": "bash",
            "description": "Execute a bash command",
            "schema": bash.BashTool().get_schema()["input_schema"]
        },
        {
            "name": "read",
            "description": "Read file contents",
            "schema": file_read.FileReadTool().get_schema()["input_schema"]
        },
        {
            "name": "write",
            "description": "Write content to a file",
            "schema": file_write.FileWriteTool().get_schema()["input_schema"]
        },
        {
            "name": "edit",
            "description": "Edit a file",
            "schema": file_edit.FileEditTool().get_schema()["input_schema"]
        },
        {
            "name": "glob",
            "description": "Find files by pattern",
            "schema": glob.GlobTool().get_schema()["input_schema"]
        },
        {
            "name": "grep",
            "description": "Search text in files",
            "schema": grep.GrepTool().get_schema()["input_schema"]
        },
        {
            "name": "web_search",
            "description": "Search the web",
            "schema": web_search.WebSearchTool().get_schema()["input_schema"]
        },
        {
            "name": "web_fetch",
            "description": "Fetch URL content",
            "schema": web_fetch.WebFetchTool().get_schema()["input_schema"]
        },
        {
            "name": "task",
            "description": "Manage tasks",
            "schema": task.TaskTool().get_schema()["input_schema"]
        }
    ]

    return {"tools": tools}


@router.post("/tools/execute")
async def execute_tool(request: ToolCallRequest) -> dict:
    """Execute a tool"""
    tool_name = request.name
    arguments = request.arguments

    try:
        if tool_name == "bash":
            from ...tools.definitions.bash import execute_bash
            result = await execute_bash(
                command=arguments.get("command"),
                timeout=arguments.get("timeout", 60)
            )
        elif tool_name == "read":
            from ...tools.definitions.file_read import read_file
            result = await read_file(path=arguments["path"])
        elif tool_name == "write":
            from ...tools.definitions.file_write import write_file
            result = await write_file(
                path=arguments["path"],
                content=arguments["content"]
            )
        elif tool_name == "edit":
            from ...tools.definitions.file_edit import edit_file
            result = await edit_file(
                path=arguments["path"],
                old_text=arguments["old_text"],
                new_text=arguments["new_text"]
            )
        elif tool_name == "glob":
            from ...tools.definitions.glob import glob_files
            result = await glob_files(pattern=arguments["pattern"])
        elif tool_name == "grep":
            from ...tools.definitions.grep import grep
            result = await grep(
                pattern=arguments["pattern"],
                path=arguments.get("path")
            )
        elif tool_name == "web_search":
            from ...tools.definitions.web_search import web_search
            result = await web_search(query=arguments["query"])
        elif tool_name == "web_fetch":
            from ...tools.definitions.web_fetch import web_fetch
            result = await web_fetch(url=arguments["url"])
        elif tool_name == "task":
            from ...tools.definitions.task import get_task_tool
            tool = get_task_tool()
            result = await tool.execute(
                action=arguments.get("action"),
                task_id=arguments.get("task_id"),
                title=arguments.get("title")
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))