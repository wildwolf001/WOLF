"""
Skill Registry - 技能注册表（类似 ToolRegistry 模式）
参考 cc-haha-main/src/skills/bundledSkills.ts
"""
import logging
from typing import Dict, List, Optional

from .types import SkillDefinition

logger = logging.getLogger(__name__)


class SkillRegistry:
    """技能注册表 - 管理所有可用的 skills"""

    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        """注册 skill（后注册的同名 skill 覆盖先注册的）"""
        name = skill.name
        if name in self._skills:
            old = self._skills[name]
            # Bundled skills are lowest priority; don't overwrite with bundled
            if old.source != 'bundled' and skill.source == 'bundled':
                return
            # User/project skills can override bundled
            logger.debug(f"Skill '{name}' overridden: {old.source} → {skill.source}")
        self._skills[name] = skill

    def get(self, name: str) -> Optional[SkillDefinition]:
        """按名称获取 skill"""
        return self._skills.get(name)

    def list_skills(self) -> List[SkillDefinition]:
        """列出所有已注册的 skills"""
        return list(self._skills.values())

    def list_invocable(self) -> List[SkillDefinition]:
        """列出可由 LLM 自动调用的 skills"""
        return [
            s for s in self._skills.values()
            if not s.frontmatter.disable_model_invocation
        ]

    def count(self) -> int:
        """返回已注册的 skill 数量"""
        return len(self._skills)

    def clear(self) -> None:
        """清空所有 skills"""
        self._skills.clear()

    def get_by_source(self, source: str) -> List[SkillDefinition]:
        """按来源筛选 skills"""
        return [s for s in self._skills.values() if s.source == source]

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __len__(self) -> int:
        return len(self._skills)

    def __iter__(self):
        return iter(self._skills.values())


# 全局单例
skill_registry = SkillRegistry()
