"""
Skills Module - WOLF Skill System
参考 cc-haha-main/src/skills/

提供:
- SKILL.md 加载与解析
- Skill 注册表
- 系统提示词注入
- Skill 工具函数
"""
from .types import SkillFrontmatter, SkillDefinition
from .registry import SkillRegistry, skill_registry
from .loader import load_skills, reload_skills, parse_skill_md
from .listing import get_skills_section, format_skill_for_prompt

__all__ = [
    'SkillFrontmatter',
    'SkillDefinition',
    'SkillRegistry',
    'skill_registry',
    'load_skills',
    'reload_skills',
    'parse_skill_md',
    'get_skills_section',
    'format_skill_for_prompt',
]
