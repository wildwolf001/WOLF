"""
Skills - 技能系统

WOLF Agent可用的技能集合
"""
import os
from typing import List, Dict, Any


SKILLS_DIR = os.path.dirname(__file__)


def list_skills() -> List[Dict[str, Any]]:
    """列出所有可用技能"""
    skills = []

    if not os.path.exists(SKILLS_DIR):
        return skills

    for skill_name in os.listdir(SKILLS_DIR):
        skill_path = os.path.join(SKILLS_DIR, skill_name)

        # 跳过__pycache__等
        if skill_name.startswith('__') or not os.path.isdir(skill_path):
            continue

        # 查找skill.md
        skill_md = os.path.join(skill_path, "skill.md")
        if os.path.exists(skill_md):
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
                # 提取description
                desc = ""
                for line in content.split('\n'):
                    if line.startswith('## Description'):
                        continue
                    if line.startswith('#'):
                        break
                    if line.strip():
                        desc = line.strip()
                        break

            skills.append({
                "name": skill_name,
                "description": desc,
                "path": skill_path
            })

    return skills


def get_skill(skill_name: str) -> Dict[str, Any]:
    """获取技能详情"""
    skill_path = os.path.join(SKILLS_DIR, skill_name)

    if not os.path.exists(skill_path):
        return None

    skill_md = os.path.join(skill_path, "skill.md")
    if not os.path.exists(skill_md):
        return None

    with open(skill_md, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        "name": skill_name,
        "content": content,
        "path": skill_path
    }


__all__ = ["list_skills", "get_skill"]