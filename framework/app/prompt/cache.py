"""
Section 级缓存 — 对标 CC systemPromptSections.ts
Static 部分跨会话复用 (global scope)，Dynamic 部分按需失效
"""
from typing import Callable, Dict, Optional
from .core.schemas import CacheScope


class SectionCache:
    """Section 级 Prompt 缓存"""

    def __init__(self):
        self._global_cache: Dict[str, str] = {}   # 跨会话复用 (对标 CC global)
        self._session_cache: Dict[str, str] = {}   # 当前会话 (对标 CC session)

    def get_or_compute(self, name: str, compute_fn: Callable[[], str],
                       scope: CacheScope = CacheScope.SESSION) -> str:
        """获取缓存值，未命中则计算并缓存"""
        cache = self._global_cache if scope == CacheScope.GLOBAL else self._session_cache
        if name not in cache:
            cache[name] = compute_fn()
        return cache[name]

    def invalidate_section(self, name: str):
        """失效指定 Section (对标 CC /clear 时清理)"""
        self._session_cache.pop(name, None)

    def invalidate_all(self):
        """失效所有 Session 级缓存"""
        self._session_cache.clear()

    def set_global(self, name: str, value: str):
        """写入 Global 缓存 (跨用户复用)"""
        self._global_cache[name] = value

    @property
    def session_size(self) -> int:
        return len(self._session_cache)

    @property
    def global_size(self) -> int:
        return len(self._global_cache)


_section_cache: Optional[SectionCache] = None


def get_section_cache() -> SectionCache:
    global _section_cache
    if _section_cache is None:
        _section_cache = SectionCache()
    return _section_cache
