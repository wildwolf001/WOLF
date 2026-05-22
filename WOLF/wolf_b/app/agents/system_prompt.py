"""
System Prompt 管理模块

参考 cc-haha 的 systemPromptSections 设计：
1. SystemPromptSection - 缓存的section，计算一次持续使用
2. VolatileSection - 每次turn都重新计算的section
3. SystemPromptCache - 缓存管理

目标：将 System Prompt 从 ~7000 tokens 简化到 ~1500 tokens
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import time
import hashlib


@dataclass
class SystemPromptSection:
    """
    单个 System Prompt Section

    属性:
        name: section 名称
        content: 如果是字符串，直接使用；如果是函数，每次调用
        cacheable: 是否缓存（False = 每次重算）
        cache_key: 缓存key，用于判断内容是否变化
        last_compute: 上次计算时间
        compute_fn: 计算函数（可选）
    """
    name: str
    content: str = ""
    cacheable: bool = True
    cache_key: str = ""
    last_compute: float = 0
    compute_fn: Optional[Callable[[], str]] = None

    def get_content(self) -> str:
        """获取section内容"""
        if self.compute_fn and not self.cacheable:
            return self.compute_fn()
        return self.content

    def compute(self) -> str:
        """计算并缓存内容"""
        if self.compute_fn:
            self.content = self.compute_fn()
            self.cache_key = self._compute_hash(self.content)
            self.last_compute = time.time()
        return self.content

    def _compute_hash(self, content: str) -> str:
        """计算内容hash"""
        return hashlib.md5(content.encode()).hexdigest()

    def should_rebuild(self) -> bool:
        """检查是否需要重建"""
        if not self.cacheable:
            return True
        if not self.content:
            return True
        return False


class SystemPromptCache:
    """
    System Prompt 缓存管理器

    参考 cc-haha 的 systemPromptSectionCache 设计：
    - 缓存sections，直到 /clear 或 /compact
    - 支持按需失效特定section
    """

    def __init__(self):
        self._sections: Dict[str, SystemPromptSection] = {}
        self._cache_hit_count = 0
        self._cache_miss_count = 0

    def register_section(self, name: str, section: SystemPromptSection) -> None:
        """注册一个section"""
        self._sections[name] = section

    def get_section(self, name: str) -> Optional[SystemPromptSection]:
        """获取section"""
        return self._sections.get(name)

    def get_content(self, name: str) -> str:
        """获取section内容（自动计算）"""
        section = self._sections.get(name)
        if not section:
            return ""

        if section.cacheable and section.content:
            self._cache_hit_count += 1
            return section.content

        self._cache_miss_count += 1
        return section.compute()

    def get_all_cached(self) -> Dict[str, str]:
        """获取所有缓存的section内容"""
        result = {}
        for name, section in self._sections.items():
            if section.cacheable and section.content:
                result[name] = section.content
        return result

    def invalidate(self, name: str) -> None:
        """使某个section失效，下次使用时重新计算"""
        if name in self._sections:
            section = self._sections[name]
            section.content = ""
            section.cache_key = ""

    def invalidate_all(self) -> None:
        """使所有section失效"""
        for section in self._sections.values():
            section.content = ""
            section.cache_key = ""

    def build_prompt(self, section_names: List[str] = None) -> str:
        """
        构建完整的 system prompt

        Args:
            section_names: 要包含的section列表，None表示包含所有

        Returns:
            组合后的 system prompt
        """
        sections_to_include = section_names or list(self._sections.keys())

        parts = []
        for name in sections_to_include:
            if name in self._sections:
                content = self.get_content(name)
                if content:
                    parts.append(content)

        return "\n\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "section_count": len(self._sections),
            "cache_hits": self._cache_hit_count,
            "cache_misses": self._cache_miss_count,
            "sections": {
                name: {
                    "cacheable": s.cacheable,
                    "content_length": len(s.content),
                    "last_compute": s.last_compute
                }
                for name, s in self._sections.items()
            }
        }


# 全局缓存实例
system_prompt_cache = SystemPromptCache()


def register_system_section(
    name: str,
    content: str = "",
    cacheable: bool = True,
    compute_fn: Optional[Callable[[], str]] = None
) -> SystemPromptSection:
    """
    注册一个 system prompt section

    Args:
        name: section 名称
        content: 静态内容
        cacheable: 是否缓存
        compute_fn: 计算函数（用于动态内容）
    """
    section = SystemPromptSection(
        name=name,
        content=content,
        cacheable=cacheable,
        compute_fn=compute_fn
    )
    system_prompt_cache.register_section(name, section)
    return section


def get_system_prompt(section_names: List[str] = None) -> str:
    """
    获取 system prompt

    Args:
        section_names: 要包含的section列表
    """
    return system_prompt_cache.build_prompt(section_names)


def invalidate_system_section(name: str) -> None:
    """使某个section失效"""
    system_prompt_cache.invalidate(name)


def clear_system_prompt_cache() -> None:
    """清空所有缓存"""
    system_prompt_cache.invalidate_all()