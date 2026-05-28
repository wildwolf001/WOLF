"""
Common Prompt Utilities
"""
from typing import List, Dict, Any


def format_file_list(files: List[str]) -> str:
    """Format a list of files for the prompt"""
    if not files:
        return "No files"
    return "\n".join(f"- {f}" for f in files)


def format_error(error: str) -> str:
    """Format an error message"""
    return f"Error: {error}"


def format_tool_result(tool: str, result: Any, success: bool = True) -> str:
    """Format a tool result"""
    status = "OK" if success else "FAILED"
    return f"[{tool}] {status}: {result}"


def format_context_summary(
    files: List[str],
    active_tools: List[str],
    turn: int
) -> str:
    """Format a context summary"""
    return f"""## Session Context
Turn: {turn}
Files: {len(files)}
Active Tools: {', '.join(active_tools) if active_tools else 'None'}"""


def get_concise_instruction() -> str:
    """Get concise instruction for quick tasks"""
    return "Be concise. Provide direct answers and minimal explanations for simple tasks."


def get_detailed_instruction() -> str:
    """Get detailed instruction for complex tasks"""
    return """For complex tasks:
1. Understand the requirements
2. Plan the approach
3. Implement incrementally
4. Verify the results"""


def get_revision_instruction() -> str:
    """Get instruction for revisions"""
    return """When revising code:
1. Understand what needs to change
2. Make minimal targeted changes
3. Verify the change doesn't break existing functionality"""