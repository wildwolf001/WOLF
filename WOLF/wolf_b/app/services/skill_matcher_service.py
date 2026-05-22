"""
Skill Matcher Service - 技能匹配和触发系统
支持被动触发（上下文匹配）和主动触发（显式调用）
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import re

router = APIRouter()

# Skill 定义
class Skill(BaseModel):
    id: str
    name: str
    description: str
    category: str
    risk: str
    content: str  # 完整的 skill markdown 内容
    triggers: List[str]  # 触发关键词
    examples: List[str]
    source: str = "custom"
    enabled: bool = True


# Skill 存储
skills_db: Dict[str, Skill] = {}


def load_skills_from_directory(skills_dir: str) -> Dict[str, Skill]:
    """从目录加载 skills"""
    if not os.path.exists(skills_dir):
        return {}

    loaded = {}
    for item in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, item)
        if os.path.isdir(skill_path):
            # 查找 skill.md 或 index.md
            for md_file in ['skill.md', 'index.md', 'README.md']:
                md_path = os.path.join(skill_path, md_file)
                if os.path.exists(md_path):
                    with open(md_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 解析 frontmatter 或从内容提取 metadata
                    triggers = extract_triggers(content)
                    name = extract_name(content, item)

                    skill = Skill(
                        id=f"skill-{item}",
                        name=name,
                        description=extract_description(content),
                        category=extract_category(content) or "general",
                        risk=extract_risk(content) or "safe",
                        content=content,
                        triggers=triggers,
                        examples=extract_examples(content),
                        source="imported"
                    )
                    loaded[skill.id] = skill
                    break

    return loaded


def extract_triggers(content: str) -> List[str]:
    """从 markdown 内容提取 triggers"""
    triggers = []
    # 查找 triggers 部分
    triggers_match = re.search(r'(?i)triggers?:\s*\[(.*?)\]', content, re.DOTALL)
    if triggers_match:
        triggers_str = triggers_match.group(1)
        triggers = [t.strip().strip('"\'') for t in triggers_str.split(',')]
    return triggers


def extract_name(content: str, default: str) -> str:
    """提取 skill 名称"""
    # 查找 # 标题
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    return default.replace('-', ' ').replace('_', ' ').title()


def extract_description(content: str) -> str:
    """提取 skill 描述"""
    desc_match = re.search(r'(?i)##?\s*(description|when to use|overview):?\s*(.+?)(?=\n\n|\n##)', content, re.DOTALL)
    if desc_match:
        return desc_match.group(2).strip()[:200]
    return ""


def extract_category(content: str) -> str:
    """提取 category"""
    cat_match = re.search(r'(?i)category:\s*(\w+)', content)
    if cat_match:
        return cat_match.group(1)
    return "general"


def extract_risk(content: str) -> str:
    """提取 risk level"""
    risk_match = re.search(r'(?i)risk:\s*(\w+)', content)
    if risk_match:
        return risk_match.group(1)
    return "safe"


def extract_examples(content: str) -> List[str]:
    """提取 examples"""
    examples = []
    example_matches = re.findall(r'(?i)(?:example|usage):\s*[`"]?(.+?)[`"]?(?=\n|$)', content, re.DOTALL)
    for ex in example_matches[:3]:
        examples.append(ex.strip())
    return examples


class MatchRequest(BaseModel):
    context: str  # 当前上下文（任务描述、对话等）
    limit: int = 5  # 最多返回多少个匹配


class ActivateRequest(BaseModel):
    skill_id: str
    context: Optional[str] = None


@router.post("/skills/match")
async def match_skills(request: MatchRequest) -> Dict[str, Any]:
    """根据上下文被动匹配 skills"""
    context_lower = request.context.lower()
    matched_skills = []

    for skill in skills_db.values():
        if not skill.enabled:
            continue

        score = 0
        matched_triggers = []

        # 检查触发词匹配
        for trigger in skill.triggers:
            trigger_lower = trigger.lower()
            if trigger_lower in context_lower:
                score += 1
                matched_triggers.append(trigger)

        # 检查名称/描述匹配
        if skill.name.lower() in context_lower:
            score += 2
        if skill.description.lower() in context_lower:
            score += 1

        if score > 0:
            matched_skills.append({
                "skill": skill,
                "score": score,
                "matched_triggers": matched_triggers
            })

    # 按分数排序
    matched_skills.sort(key=lambda x: x["score"], reverse=True)

    return {
        "matched_count": len(matched_skills),
        "context": request.context[:100],
        "skills": [
            {
                "id": s["skill"].id,
                "name": s["skill"].name,
                "category": s["skill"].category,
                "score": s["score"],
                "matched_triggers": s["matched_triggers"],
                "description": s["skill"].description
            }
            for s in matched_skills[:request.limit]
        ]
    }


@router.post("/skills/activate")
async def activate_skill(request: ActivateRequest) -> Dict[str, Any]:
    """主动触发某个 skill"""
    skill = skills_db.get(request.skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if not skill.enabled:
        raise HTTPException(status_code=400, detail="Skill is disabled")

    return {
        "success": True,
        "skill_id": skill.id,
        "name": skill.name,
        "content": skill.content,
        "context": request.context
    }


@router.get("/skills/trigger/{keyword}")
async def trigger_by_keyword(keyword: str) -> Dict[str, Any]:
    """根据关键词触发 skill（用于自动化场景）"""
    keyword_lower = keyword.lower()

    for skill in skills_db.values():
        if not skill.enabled:
            continue

        for trigger in skill.triggers:
            if trigger.lower() == keyword_lower or keyword_lower in trigger.lower():
                return {
                    "matched": True,
                    "skill": {
                        "id": skill.id,
                        "name": skill.name,
                        "content": skill.content,
                        "triggers": skill.triggers
                    }
                }

    return {"matched": False, "message": f"No skill found for keyword: {keyword}"}


@router.get("/skills")
async def list_skills(category: Optional[str] = None, enabled: Optional[bool] = None) -> List[dict]:
    """列出所有 skills"""
    skills = list(skills_db.values())

    if category:
        skills = [s for s in skills if s.category == category]
    if enabled is not None:
        skills = [s for s in skills if s.enabled == enabled]

    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "category": s.category,
            "risk": s.risk,
            "triggers": s.triggers,
            "examples": s.examples,
            "enabled": s.enabled
        }
        for s in skills
    ]


@router.post("/skills/import")
async def import_skills_from_path(path: str) -> Dict[str, Any]:
    """从指定路径导入 skills"""
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Path not found")

    imported = load_skills_from_directory(path)
    count = 0

    for skill in imported.values():
        skills_db[skill.id] = skill
        count += 1

    return {
        "success": True,
        "imported_count": count,
        "skills": list(imported.keys())
    }


@router.post("/skills")
async def create_skill(skill: Skill) -> dict:
    """创建新 skill"""
    skills_db[skill.id] = skill
    return {"success": True, "skill_id": skill.id}


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str) -> dict:
    """删除 skill"""
    if skill_id in skills_db:
        del skills_db[skill_id]
    return {"success": True}


# 初始化时尝试加载 cc-haha-main 的 skills
SKILLS_PATH = "E:/agent/claude/cc-haha-main/src/skills"
_initialized = False

def initialize_skills():
    global _initialized
    if not _initialized:
        loaded = load_skills_from_directory(SKILLS_PATH)
        for skill in loaded.values():
            skills_db[skill.id] = skill
        _initialized = True
        print(f"Loaded {len(loaded)} skills from {SKILLS_PATH}")

# 启动时初始化（可以延迟到第一次调用）
try:
    initialize_skills()
except Exception as e:
    print(f"Warning: Could not load skills: {e}")