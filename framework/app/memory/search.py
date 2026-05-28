"""
Memory Search Service
参考 cc-haha-main/src/memdir/findRelevantMemories.ts

记忆检索服务
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .types import MemoryEntry, MemoryTypeEnum, parse_memory_type
from .directory import get_memory_directory, MemoryDirectory, DEFAULT_MEMORY_DIR


class MemorySearchService:
    """记忆检索服务"""

    def __init__(self, memory_dir: Optional[str] = None):
        if memory_dir:
            self._memory_dir = MemoryDirectory(memory_dir)
        else:
            self._memory_dir = get_memory_directory()

    @property
    def directory(self) -> MemoryDirectory:
        return self._memory_dir

    def find_by_type(self, memory_type: MemoryTypeEnum) -> List[MemoryEntry]:
        """按类型查找记忆"""
        results = []
        for _, entry in self._memory_dir.list_memory_files():
            if entry.memory_type == memory_type:
                results.append(entry)
        return results

    def find_by_keyword(self, keyword: str, case_sensitive: bool = False) -> List[Tuple[str, MemoryEntry]]:
        """按关键词搜索记忆"""
        results = []
        keyword_lower = keyword.lower() if not case_sensitive else keyword

        for filepath, entry in self._memory_dir.list_memory_files():
            if not case_sensitive:
                matches = (
                    keyword_lower in entry.name.lower() or
                    keyword_lower in entry.description.lower() or
                    keyword_lower in entry.content.lower()
                )
            else:
                matches = (
                    keyword in entry.name or
                    keyword in entry.description or
                    keyword in entry.content
                )

            if matches:
                results.append((filepath, entry))

        return results

    def find_relevant(self, query: str, memory_types: Optional[List[MemoryTypeEnum]] = None, max_results: int = 5) -> List[MemoryEntry]:
        """查找与查询相关的记忆"""
        candidates = self.find_by_keyword(query)

        if memory_types:
            candidates = [(fp, entry) for fp, entry in candidates if entry.memory_type in memory_types]

        scored = []
        query_lower = query.lower()
        for filepath, entry in candidates:
            score = 0
            if query_lower in entry.name.lower():
                score += 10
            if query_lower in entry.description.lower():
                score += 5
            if query_lower in entry.content.lower():
                score += 1
            scored.append((score, filepath, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, _, entry in scored[:max_results]]

    def search_content(self, pattern: str, regex: bool = False, case_sensitive: bool = True) -> List[Tuple[str, int, str]]:
        """在记忆文件中搜索内容"""
        results = []
        memory_dir = Path(self._memory_dir.path)

        for md_file in memory_dir.glob('*.md'):
            if md_file.name == 'MEMORY.md':
                continue

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    for line_no, line in enumerate(f, 1):
                        if regex:
                            if re.search(pattern, line):
                                results.append((str(md_file), line_no, line.rstrip()))
                        else:
                            if (case_sensitive and pattern in line) or \
                               (not case_sensitive and pattern.lower() in line.lower()):
                                results.append((str(md_file), line_no, line.rstrip()))
            except Exception:
                continue

        return results

    def get_all_memories(self) -> List[MemoryEntry]:
        return [entry for _, entry in self._memory_dir.list_memory_files()]

    def get_memory_stats(self) -> dict:
        entries = self.get_all_memories()
        by_type = {}
        for entry in entries:
            t = entry.memory_type.value
            by_type[t] = by_type.get(t, 0) + 1

        return {
            'total': len(entries),
            'by_type': by_type,
            'memory_dir': self._memory_dir.path,
        }

    def search_by_name(self, name: str) -> Optional[MemoryEntry]:
        """按名称精确查找记忆"""
        for _, entry in self._memory_dir.list_memory_files():
            if entry.name == name:
                return entry
        return None


_memory_search: Optional[MemorySearchService] = None


def get_memory_search_service(memory_dir: Optional[str] = None) -> MemorySearchService:
    global _memory_search
    if _memory_search is None:
        _memory_search = MemorySearchService(memory_dir)
    return _memory_search


def reset_memory_search() -> None:
    global _memory_search
    _memory_search = None