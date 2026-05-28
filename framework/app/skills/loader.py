"""
Skill Loader - 从磁盘加载 SKILL.md 文件
参考 cc-haha-main/src/skills/loadSkillsDir.ts

扫描目录:
1. Project: {project_root}/.claude/skills/*/SKILL.md
2. User: ~/.wolf/skills/*/SKILL.md
3. Bundled: wolf_b2/app/skills/bundled/*/SKILL.md
"""
import os
import re
import logging
from pathlib import Path
from typing import List, Optional

import yaml

from .types import SkillFrontmatter, SkillDefinition
from .registry import skill_registry

logger = logging.getLogger(__name__)


def parse_skill_md(filepath: str) -> Optional[SkillDefinition]:
    """
    解析单个 SKILL.md 文件。

    格式:
    ---
    name: skill-name
    description: "..."
    ---
    # Body (markdown)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.warning(f"Failed to read {filepath}: {e}")
        return None

    # Split by --- delimiters to extract frontmatter
    parts = content.split('---', 2)
    if len(parts) < 3:
        logger.warning(f"No valid frontmatter found in {filepath}")
        return None

    yaml_str = parts[1].strip()
    body = parts[2].strip()

    try:
        raw = yaml.safe_load(yaml_str)
        if not isinstance(raw, dict):
            logger.warning(f"Invalid YAML frontmatter in {filepath}")
            return None
    except yaml.YAMLError as e:
        logger.warning(f"YAML parse error in {filepath}: {e}")
        return None

    name = raw.get('name', '')
    if not name:
        logger.warning(f"Missing 'name' in {filepath}")
        return None

    frontmatter = SkillFrontmatter(
        name=name,
        description=raw.get('description', ''),
        allowed_tools=raw.get('allowed-tools', raw.get('allowed_tools', [])),
        when_to_use=raw.get('when_to_use'),
        user_invocable=raw.get('user-invocable', raw.get('user_invocable', True)),
        disable_model_invocation=raw.get(
            'disable-model-invocation',
            raw.get('disable_model_invocation', False)
        ),
        context=raw.get('context', 'inline'),
        version=raw.get('version'),
        model=raw.get('model'),
        paths=raw.get('paths', []),
    )

    return SkillDefinition(
        frontmatter=frontmatter,
        body=body,
        source_path=filepath,
        source='unknown',  # will be set by caller
    )


def scan_skill_dir(base_dir: str, source: str) -> List[SkillDefinition]:
    """
    扫描目录下的所有 SKILL.md 文件。
    查找模式: {base_dir}/*/SKILL.md
    """
    skills: List[SkillDefinition] = []
    if not os.path.isdir(base_dir):
        return skills

    for entry in os.scandir(base_dir):
        if not entry.is_dir():
            continue
        skill_md = os.path.join(entry.path, 'SKILL.md')
        if os.path.isfile(skill_md):
            skill = parse_skill_md(skill_md)
            if skill:
                skill.source = source
                skills.append(skill)
                logger.info(f"Loaded skill '{skill.name}' from {source}: {skill_md}")

    return skills


def get_project_root() -> str:
    """获取项目根目录（wolf_b2 的父目录）"""
    current = os.path.dirname(os.path.abspath(__file__))
    # Go up from app/skills/ → app/ → wolf_b2/
    while current and os.path.basename(current) != 'wolf_b2':
        current = os.path.dirname(current)
    if not current:
        return os.getcwd()
    # Project root is the parent of wolf_b2 (i.e., WOLF2.0)
    return os.path.dirname(current)


def get_bundled_skills_dir() -> str:
    """获取内置 skills 目录"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bundled')


def load_skills() -> int:
    """
    加载所有 skills:
    1. Bundled: 最高优先级（系统内置）
    2. User: ~/.wolf/skills/
    3. Project: {project_root}/.claude/skills/

    Returns: 加载的 skill 总数
    """
    total = 0

    # 1. Bundled skills (loaded first, lowest priority)
    bundled_dir = get_bundled_skills_dir()
    bundled = scan_skill_dir(bundled_dir, 'bundled')
    for skill in bundled:
        skill_registry.register(skill)
        total += 1

    # 2. User skills (~/.wolf/skills/)
    user_dir = os.path.join(os.path.expanduser('~'), '.wolf', 'skills')
    user_skills = scan_skill_dir(user_dir, 'user')
    for skill in user_skills:
        skill_registry.register(skill)
        total += 1

    # 3. Project skills ({project_root}/.claude/skills/)
    project_root = get_project_root()
    project_dir = os.path.join(project_root, '.claude', 'skills')
    project_skills = scan_skill_dir(project_dir, 'project')
    for skill in project_skills:
        skill_registry.register(skill)
        total += 1

    # Also check CLAUDE.md-style commands directory
    commands_dir = os.path.join(project_root, '.claude', 'commands')
    if os.path.isdir(commands_dir):
        for entry in os.scandir(commands_dir):
            if entry.is_file() and entry.name.endswith('.md'):
                skill = parse_skill_md(entry.path)
                if skill:
                    skill.source = 'project'
                    skill_registry.register(skill)
                    total += 1
                    logger.info(f"Loaded skill '{skill.name}' from commands dir: {entry.path}")

    logger.info(f"Skills loaded: {total} total")
    return total


def reload_skills() -> int:
    """重新加载所有 skills"""
    skill_registry.clear()
    return load_skills()
