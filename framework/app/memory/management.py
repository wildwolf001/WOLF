"""
Memory Management Service
记忆的更新、删除、整理
"""

from typing import Optional, List
from datetime import datetime, timedelta

from .types import MemoryEntry, MemoryTypeEnum, parse_memory_type
from .directory import get_memory_directory, MemoryDirectory
from .search import get_memory_search_service, MemorySearchService


class MemoryManagementService:
    """记忆管理服务"""

    def __init__(self, memory_dir: Optional[str] = None):
        if memory_dir:
            self._memory_dir = MemoryDirectory(memory_dir)
            self._search = MemorySearchService(memory_dir)
        else:
            self._memory_dir = get_memory_directory()
            self._search = get_memory_search_service()

    @property
    def directory(self) -> MemoryDirectory:
        return self._memory_dir

    @property
    def search(self) -> MemorySearchService:
        return self._search

    def update_memory(self, filename: str, updates: dict) -> bool:
        """更新记忆文件"""
        entry = self._memory_dir.read_memory_file(filename)
        if not entry:
            return False

        old_filename = filename

        if 'name' in updates:
            entry.name = updates['name']
        if 'description' in updates:
            entry.description = updates['description']
        if 'content' in updates:
            entry.content = updates['content']

        entry.updated_at = datetime.utcnow()

        if old_filename != filename:
            self._memory_dir.delete_memory(old_filename)

        self._memory_dir.write_memory(entry)
        return True

    def delete_memory(self, filename: str) -> bool:
        return self._memory_dir.delete_memory(filename)

    def delete_by_name(self, name: str) -> bool:
        entry = self._search.search_by_name(name)
        if not entry:
            return False

        safe_name = name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '_-')[:50]
        filename = f"{entry.memory_type.value}_{safe_name}.md"

        return self._memory_dir.delete_memory(filename)

    def delete_by_type(self, memory_type: MemoryTypeEnum) -> int:
        count = 0
        for filepath, entry in self._search.find_by_type(memory_type):
            filename = filepath.split('/')[-1]
            if self._memory_dir.delete_memory(filename):
                count += 1
        return count

    def prune_old_memories(self, days: int = 90) -> int:
        """清理超过指定天数的记忆"""
        count = 0
        cutoff = datetime.utcnow() - timedelta(days=days)

        for filepath, entry in self._memory_dir.list_memory_files():
            if entry.updated_at < cutoff:
                filename = filepath.split('/')[-1]
                if self._memory_dir.delete_memory(filename):
                    count += 1

        return count

    def rebuild_entrypoint(self) -> None:
        """重建 MEMORY.md 索引"""
        entries = self._search.get_all_memories()

        with open(self._memory_dir.entrypoint_path, 'w', encoding='utf-8') as f:
            f.write('')

        for entry in entries:
            self._memory_dir.write_memory(entry)

    def get_memory_age_stats(self) -> dict:
        entries = self._search.get_all_memories()
        now = datetime.utcnow()

        ages = []
        by_type = {}
        for entry in entries:
            age_days = (now - entry.updated_at).days
            ages.append(age_days)

            t = entry.memory_type.value
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(age_days)

        if not ages:
            return {'total_memories': 0, 'avg_age_days': 0, 'min_age_days': 0, 'max_age_days': 0, 'by_type': {}}

        return {
            'total_memories': len(entries),
            'avg_age_days': sum(ages) // len(ages),
            'min_age_days': min(ages),
            'max_age_days': max(ages),
            'by_type': {t: {'count': len(ages_list), 'avg_age': sum(ages_list) // len(ages_list) if ages_list else 0} for t, ages_list in by_type.items()}
        }


_memory_management: Optional[MemoryManagementService] = None


def get_memory_management_service(memory_dir: Optional[str] = None) -> MemoryManagementService:
    global _memory_management
    if _memory_management is None:
        _memory_management = MemoryManagementService(memory_dir)
    return _memory_management


def reset_memory_management() -> None:
    global _memory_management
    _memory_management = None