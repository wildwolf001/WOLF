"""
Snippet Compaction
Creates compact snippets from larger content
"""
import re
from typing import List, Dict, Any, Optional, Tuple


class SnipCompactor:
    """
    Creates compact snippets from larger content.
    Useful for summarizing tool results or long file contents.
    """

    def __init__(
        self,
        max_snippet_length: int = 500,
        max_lines: int = 50,
        preserve_patterns: Optional[List[str]] = None
    ):
        self._max_snippet_length = max_snippet_length
        self._max_lines = max_lines
        self._preserve_patterns = preserve_patterns or []

    def snip(
        self,
        content: str,
        max_length: Optional[int] = None,
        max_lines: Optional[int] = None
    ) -> str:
        """
        Create a snippet from content.
        """
        max_len = max_length or self._max_snippet_length
        max_l = max_lines or self._max_lines

        # Split into lines
        lines = content.split('\n')
        if len(lines) > max_l:
            # Keep first and last few lines
            keep_lines = min(5, max_l // 2)
            snippet_lines = lines[:keep_lines] + ['...'] + lines[-keep_lines:]
            content = '\n'.join(snippet_lines)

        # Truncate if still too long
        if len(content) > max_len:
            return content[:max_len] + '...'

        return content

    def snip_code(
        self,
        code: str,
        max_lines: Optional[int] = None
    ) -> str:
        """
        Create a snippet from code, preserving structure.
        """
        max_l = max_lines or self._max_lines
        lines = code.split('\n')

        if len(lines) <= max_l:
            return code

        # Keep structure: first N lines, ellipsis, last M lines
        keep = 10
        snippet = '\n'.join(lines[:keep])
        snippet += f'\n# ... {len(lines) - keep * 2} lines hidden ...'
        snippet += '\n' + '\n'.join(lines[-keep:])

        return snippet

    def preserve_and_snip(
        self,
        content: str,
        patterns: List[str],
        max_length: Optional[int] = None
    ) -> str:
        """
        Preserve content matching patterns, then snip the rest.
        """
        max_len = max_length or self._max_snippet_length

        preserved = []
        rest = []

        for line in content.split('\n'):
            if any(re.search(p, line) for p in patterns):
                preserved.append(line)
            else:
                rest.append(line)

        # Combine and snip
        result = '\n'.join(preserved + rest)
        if len(result) > max_len:
            return result[:max_len] + '...'

        return result


def snip_tool_result(result: Any, max_length: int = 500) -> str:
    """
    Snip a tool result for inclusion in context.
    """
    result_str = str(result)
    if len(result_str) <= max_length:
        return result_str
    return result_str[:max_length] + '...'


def snip_file_content(content: str, max_lines: int = 100) -> str:
    """
    Snip file content for context.
    """
    lines = content.split('\n')
    if len(lines) <= max_lines:
        return content

    keep = max_lines // 2
    return '\n'.join(lines[:keep]) + f'\n# ... {len(lines) - keep * 2} lines hidden ...\n' + '\n'.join(lines[-keep:])