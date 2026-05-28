"""
System Prompt Sections
STATIC/DYNAMIC caching based on cc-haha systemPromptSections.ts
"""
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import asyncio


class CacheMode(Enum):
    """Cache mode for prompt sections"""
    STATIC = "static"  # Long-term cache
    DYNAMIC = "dynamic"  # Recompute every turn


@dataclass
class PromptSection:
    """A section of the system prompt"""
    name: str
    compute: Callable[[], str]
    cache_mode: CacheMode


class SystemPromptSectionCache:
    """
    Cache for system prompt sections.
    STATIC sections are cached long-term, DYNAMIC sections recompute each turn.
    """
    _instance: Optional['SystemPromptSectionCache'] = None

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._sections: List[PromptSection] = []
        self._break_cache: bool = False

    @classmethod
    def get_instance(cls) -> 'SystemPromptSectionCache':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_section(
        self,
        name: str,
        compute: Callable[[], str],
        cache_mode: CacheMode = CacheMode.STATIC
    ) -> None:
        """Register a prompt section"""
        section = PromptSection(name=name, compute=compute, cache_mode=cache_mode)
        self._sections.append(section)

        if cache_mode == CacheMode.STATIC and name not in self._cache:
            self._cache[name] = compute()

    def invalidate(self) -> None:
        """Invalidate all cache"""
        self._cache.clear()
        self._break_cache = True

    def invalidate_section(self, name: str) -> None:
        """Invalidate a specific section"""
        if name in self._cache:
            del self._cache[name]

    async def resolve(self) -> str:
        """Resolve all sections and return combined prompt"""
        parts = []

        for section in self._sections:
            if section.cache_mode == CacheMode.STATIC:
                if section.name in self._cache:
                    parts.append(self._cache[section.name])
                else:
                    value = section.compute()
                    self._cache[section.name] = value
                    parts.append(value)
            else:
                # DYNAMIC - compute each time
                parts.append(section.compute())

        return "\n\n".join(parts)

    def get_cache_break(self) -> bool:
        """Check if cache should be broken"""
        return self._break_cache

    def clear_cache_break(self) -> None:
        """Clear cache break flag"""
        self._break_cache = False


# Global cache instance
_system_prompt_cache: Optional[SystemPromptSectionCache] = None


def get_system_prompt_cache() -> SystemPromptSectionCache:
    """Get the global system prompt cache"""
    global _system_prompt_cache
    if _system_prompt_cache is None:
        _system_prompt_cache = SystemPromptSectionCache.get_instance()
    return _system_prompt_cache


def system_prompt_section(
    name: str,
    compute: Callable[[], str]
) -> PromptSection:
    """Create a static system prompt section"""
    return PromptSection(name=name, compute=compute, cache_mode=CacheMode.STATIC)


def create_uncached_section(
    name: str,
    compute: Callable[[], str],
    reason: str = ""
) -> PromptSection:
    """Create a volatile (DYNAMIC) system prompt section"""
    return PromptSection(name=name, compute=compute, cache_mode=CacheMode.DYNAMIC)


async def resolve_system_prompt_sections(
    sections: List[PromptSection]
) -> List[Optional[str]]:
    """Resolve all sections asynchronously"""
    results = []

    for section in sections:
        if section.cache_mode == CacheMode.STATIC:
            cache = get_system_prompt_cache()
            if section.name in cache._cache:
                results.append(cache._cache[section.name])
            else:
                value = section.compute()
                cache._cache[section.name] = value
                results.append(value)
        else:
            results.append(section.compute())

    return results


def clear_system_prompt_sections() -> None:
    """Clear all system prompt section state"""
    cache = get_system_prompt_cache()
    cache.invalidate()


# Common section names
SECTION_NAMES = {
    "capabilities": "capabilities",
    "context": "context",
    "tools": "tools",
    "system": "system",
    "rules": "rules"
}