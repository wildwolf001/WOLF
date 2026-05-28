"""
Memory Extraction Bridge
会话记忆到持久记忆的桥梁
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import re

from .types import MemoryEntry, MemoryTypeEnum
from .directory import get_memory_directory, MemoryDirectory
from .search import get_memory_search_service, MemorySearchService
from .management import get_memory_management_service, MemoryManagementService


class MemoryExtractionService:
    """从会话记忆中提取值得持久化的信息"""

    def __init__(self, memory_dir: Optional[str] = None):
        if memory_dir:
            self._memory_dir = MemoryDirectory(memory_dir)
            self._search = MemorySearchService(memory_dir)
            self._management = MemoryManagementService(memory_dir)
        else:
            self._memory_dir = get_memory_directory()
            self._search = get_memory_search_service()
            self._management = get_memory_management_service()

    async def extract_and_save(self, session_messages: List[Dict[str, Any]], session_summary: Optional[str] = None) -> List[str]:
        """从会话消息中提取记忆并保存"""
        saved_files = []

        if session_summary:
            memory_type = self._detect_memory_type(session_summary)
            entry = MemoryEntry(
                name=f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                description=f"Extracted from session: {session_summary[:80]}...",
                memory_type=memory_type,
                content=session_summary
            )
            filepath = self._memory_dir.write_memory(entry)
            saved_files.append(filepath)

        for msg in session_messages:
            content = msg.get('content', '')
            if not content:
                continue

            memory_type = self._detect_memory_type(content)
            if memory_type == MemoryTypeEnum.USER:
                user_info = self._extract_user_info(content)
                if user_info:
                    entry = MemoryEntry(
                        name=f"user_{datetime.utcnow().strftime('%H%M%S')}",
                        description=user_info.get('description', 'User information'),
                        memory_type=MemoryTypeEnum.USER,
                        content=user_info.get('content', content[:500])
                    )
                    filepath = self._memory_dir.write_memory(entry)
                    saved_files.append(filepath)
            elif memory_type == MemoryTypeEnum.FEEDBACK:
                feedback = self._extract_feedback(content)
                if feedback:
                    entry = MemoryEntry(
                        name=f"feedback_{datetime.utcnow().strftime('%H%M%S')}",
                        description=feedback.get('description', 'User feedback'),
                        memory_type=MemoryTypeEnum.FEEDBACK,
                        content=feedback.get('content', content[:500])
                    )
                    filepath = self._memory_dir.write_memory(entry)
                    saved_files.append(filepath)

        return saved_files

    def _detect_memory_type(self, content: str) -> MemoryTypeEnum:
        content_lower = content.lower()

        feedback_keywords = ['don\'t', 'stop', 'no not', 'never do that', 'yes exactly', 'perfect', 'wrong', 'incorrect', 'better', 'worse']
        for kw in feedback_keywords:
            if kw in content_lower:
                return MemoryTypeEnum.FEEDBACK

        project_keywords = ['deadline', 'milestone', 'team', 'release', 'bug', 'incident', 'project', 'sprint']
        for kw in project_keywords:
            if kw in content_lower:
                return MemoryTypeEnum.PROJECT

        reference_keywords = ['linear', 'jira', 'slack', 'grafana', 'dashboard', 'confluence', 'github']
        for kw in reference_keywords:
            if kw in content_lower:
                return MemoryTypeEnum.REFERENCE

        return MemoryTypeEnum.USER

    def _extract_user_info(self, content: str) -> Optional[Dict[str, str]]:
        role_patterns = [r'(?:i\'m|i am|my role is|role:|position:)\s*(.+)', r'(?:developer|engineer|manager|designer)\s*(.+)']
        for pattern in role_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return {'description': f"User role: {match.group(1)[:50]}", 'content': f"User is: {match.group(1)}\n\nFrom: {content[:500]}"}
        return None

    def _extract_feedback(self, content: str) -> Optional[Dict[str, str]]:
        correction_patterns = [(r'don\'t\s+(.+)', 'negative correction'), (r'stop\s+(.+)', 'stop request'), (r'wrong\s+(.+)', 'error correction')]
        for pattern, feedback_type in correction_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return {'description': f"User feedback: {feedback_type}", 'content': f"User: {match.group(0)}\n\nContext: {content[:500]}"}

        confirmation_patterns = [(r'yes(?:,?\s+)?exactly', 'explicit confirmation'), (r'perfect', 'positive confirmation')]
        for pattern, feedback_type in confirmation_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return {'description': f"User feedback: {feedback_type}", 'content': f"User confirmed: {match.group(0)}\n\nContext: {content[:500]}"}

        return None

    async def suggest_memories(self, recent_messages: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
        suggestions = []
        for msg in recent_messages:
            content = msg.get('content', '')
            role = msg.get('role', '')
            if role != 'user':
                continue

            correction_phrases = ['don\'t', 'stop', 'no not', 'never do that']
            for phrase in correction_phrases:
                if phrase in content.lower():
                    suggestions.append({'type': 'feedback', 'suggested_name': f"feedback_{datetime.utcnow().strftime('%H%M%S')}", 'suggested_content': content[:500], 'confidence': 0.9, 'reason': f"User correction: '{phrase}'"})
                    break

            confirmation_phrases = ['yes exactly', 'perfect', 'that\'s right']
            for phrase in confirmation_phrases:
                if phrase in content.lower():
                    suggestions.append({'type': 'feedback', 'suggested_name': f"feedback_{datetime.utcnow().strftime('%H%M%S')}", 'suggested_content': content[:500], 'confidence': 0.85, 'reason': f"User confirmation: '{phrase}'"})
                    break

        return suggestions

    def get_session_memory_summary(self, session_memory) -> str:
        recent = session_memory.get_recent(20)
        if not recent:
            return ""

        lines = ["Session Memory Summary:", ""]
        tool_calls = session_memory.get_by_type('tool_call')
        if tool_calls:
            tools = set(item.metadata.get('tool', 'unknown') for item in tool_calls)
            lines.append(f"Tools used: {', '.join(tools)}")

        messages = session_memory.get_by_type('message')
        if messages:
            lines.append(f"Messages: {len(messages)}")

        summary = session_memory.get_recent(1)
        if summary:
            lines.append(f"Last message: {summary[0].content[:100]}...")

        return "\n".join(lines)


_memory_extraction: Optional[MemoryExtractionService] = None


def get_memory_extraction_service(memory_dir: Optional[str] = None) -> MemoryExtractionService:
    global _memory_extraction
    if _memory_extraction is None:
        _memory_extraction = MemoryExtractionService(memory_dir)
    return _memory_extraction


def reset_memory_extraction() -> None:
    global _memory_extraction
    _memory_extraction = None