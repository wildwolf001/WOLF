"""
Tool-Related Prompts
"""
from typing import List, Dict, Any


TOOL_DESCRIPTIONS = {
    "read": "Read the contents of a file",
    "write": "Write content to a file",
    "edit": "Edit a specific part of a file",
    "bash": "Execute a bash command",
    "glob": "Find files matching a pattern",
    "grep": "Search for text in files",
    "list": "List directory contents",
    "exists": "Check if a file exists",
}


def format_tool_description(tool_name: str) -> str:
    """Get description for a tool"""
    return TOOL_DESCRIPTIONS.get(tool_name, f"Tool: {tool_name}")


def format_tools_list(tools: List[Dict[str, Any]]) -> str:
    """Format a list of tools in XML format"""
    parts = ["<tools>"]

    for tool in tools:
        # Support both OpenAI standard format (function wrapper) and legacy flat format
        func = tool.get("function", {})
        name = func.get("name") or tool.get("name", "unknown")
        description = func.get("description") or tool.get("description", format_tool_description(name))
        input_schema = func.get("parameters") or tool.get("input_schema", {})

        parts.append(f"  <tool name=\"{name}\">")
        parts.append(f"    <description>{description}</description>")
        parts.append(f"    <parameters>")

        properties = input_schema.get("properties", {})
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            parts.append(f"      <parameter name=\"{param_name}\" type=\"{param_type}\">{param_desc}