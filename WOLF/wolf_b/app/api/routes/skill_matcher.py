"""
Skills Management API - 技能管理和触发
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

router = APIRouter(prefix="/skills", tags=["skills"])

# Skills 存储目录
SKILLS_DIR = "E:/agent/claude/cc-haha-main/src/skills"


class SkillCreate(BaseModel):
    name: str
    description: str
    category: str = "general"
    risk: str = "safe"
    content: str
    triggers: List[str] = []
    examples: List[str] = []


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    risk: Optional[str] = None
    content: Optional[str] = None
    triggers: Optional[List[str]] = None
    enabled: Optional[bool] = None


class SkillMatchRequest(BaseModel):
    context: str
    limit: int = 5


# 全局 skills 缓存
_skills_cache: Dict[str, dict] = {}


def load_skill_content(skill_path: str) -> str:
    """加载 skill 文件内容"""
    for md_name in ['skill.md', 'index.md', 'README.md', 'SKILL.md', 'INDEX.MD']:
        md_path = os.path.join(skill_path, md_name)
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                return f.read()
    return ""


def scan_skills_directory() -> List[dict]:
    """扫描 skills 目录，返回所有 skill 的基本信息"""
    import re  # Import here to avoid global scope issues

    if not os.path.exists(SKILLS_DIR):
        print(f"Warning: Skills directory not found: {SKILLS_DIR}")
        return []

    skills = []
    for item in os.listdir(SKILLS_DIR):
        skill_path = os.path.join(SKILLS_DIR, item)
        if not os.path.isdir(skill_path):
            continue

        content = load_skill_content(skill_path)
        if not content:
            continue

        # 先尝试从 frontmatter 提取
        fm = extract_frontmatter(content)

        # 提取标题
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        name = fm.get('name', '') or (title_match.group(1).strip() if title_match else item.replace('-', ' ').title())

        # 提取触发词 - frontmatter 或 content
        triggers_str = fm.get('triggers', '')
        if triggers_str:
            triggers = [t.strip().strip('"\'') for t in triggers_str.split(',')]
        else:
            # 尝试从内容中查找 triggers
            triggers_match = re.search(r'(?i)triggers?:\s*\[(.*?)\]', content, re.DOTALL)
            triggers = []
            if triggers_match:
                triggers = [t.strip().strip('"\'') for t in triggers_match.group(1).split(',')]
            else:
                # 从 frontmatter 提取 keywords 或 keywords
                triggers_str = fm.get('keywords', fm.get('tags', ''))
                if triggers_str:
                    triggers = [t.strip() for t in triggers_str.split(',')]

        # 提取描述
        description = fm.get('description', '') or ''
        if not description:
            desc_match = re.search(r'(?i)(?:##?\s*description|when to use):?\s*(.+?)(?=\n\n|\n##)', content, re.DOTALL)
            description = desc_match.group(1).strip()[:200] if desc_match else ""

        # 提取其他字段
        category = fm.get('category', 'general')
        risk = fm.get('risk', 'safe')

        skills.append({
            "id": f"skill-{item}",
            "name": name,
            "description": description[:200] if description else "",
            "category": category,
            "risk": risk,
            "triggers": triggers,
            "path": skill_path,
            "source": "imported"
        })

    return skills


def extract_field(content: str, pattern: str, default: str = "") -> str:
    """从内容中提取字段"""
    import re
    match = re.search(pattern, content)
    return match.group(1) if match else default


def extract_frontmatter(content: str) -> dict:
    """提取 YAML frontmatter"""
    import re
    frontmatch = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not frontmatch:
        return {}

    fm = {}
    for line in frontmatch.group(1).split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            fm[key.strip()] = val.strip().strip('"\'')
    return fm


# 初始化时扫描
_initialized = False


def ensure_initialized():
    global _initialized, _skills_cache
    if not _initialized:
        _skills_cache = {s["id"]: s for s in scan_skills_directory()}
        _initialized = True


@router.get("")
async def list_all_skills(category: Optional[str] = None) -> List[dict]:
    """列出所有可用的 skills"""
    ensure_initialized()
    skills = list(_skills_cache.values())

    if category:
        skills = [s for s in skills if s.get("category") == category]

    return skills


@router.get("/trigger/{keyword}")
async def trigger_skill_by_keyword(keyword: str) -> dict:
    """
    根据关键词触发 skill（主动触发）
    用于自动化场景：当检测到特定关键词时调用此接口
    """
    ensure_initialized()
    keyword_lower = keyword.lower()

    for skill in _skills_cache.values():
        triggers = skill.get("triggers", [])
        for trigger in triggers:
            if keyword_lower == trigger.lower() or keyword_lower in trigger.lower():
                # 读取完整内容
                content = load_skill_content(skill["path"])
                return {
                    "matched": True,
                    "skill_id": skill["id"],
                    "name": skill["name"],
                    "content": content,
                    "triggers": triggers
                }

    return {"matched": False, "message": f"No skill found for: {keyword}"}


@router.post("/match")
async def match_skills_by_context(request: SkillMatchRequest) -> dict:
    """
    根据上下文匹配 skills（被动触发）
    在任务执行前调用，传入任务描述，让系统自动匹配相关 skills
    """
    ensure_initialized()
    context_lower = request.context.lower()
    matched = []

    for skill in _skills_cache.values():
        if not skill.get("enabled", True):
            continue

        score = 0
        matched_triggers = []
        triggers = skill.get("triggers", [])

        # 计算匹配分数
        for trigger in triggers:
            if trigger.lower() in context_lower:
                score += 1
                matched_triggers.append(trigger)

        if skill["name"].lower() in context_lower:
            score += 2

        if score > 0:
            matched.append({
                "id": skill["id"],
                "name": skill["name"],
                "category": skill.get("category"),
                "score": score,
                "matched_triggers": matched_triggers
            })

    # 按分数排序
    matched.sort(key=lambda x: x["score"], reverse=True)

    return {
        "context": request.context[:100],
        "matched_count": len(matched),
        "skills": matched[:request.limit]
    }


@router.get("/{skill_id}")
async def get_skill_detail(skill_id: str) -> dict:
    """获取 skill 详情"""
    ensure_initialized()

    if skill_id not in _skills_cache:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills_cache[skill_id]
    content = load_skill_content(skill["path"])

    return {
        "id": skill["id"],
        "name": skill["name"],
        "description": skill["description"],
        "category": skill.get("category"),
        "risk": skill.get("risk"),
        "triggers": skill.get("triggers", []),
        "content": content
    }


@router.post("/trigger")
async def trigger_skill(request: dict) -> dict:
    """
    手动触发 skill
    传入 skill_id 和上下文，返回 skill 内容供 agent 使用
    """
    skill_id = request.get("skill_id")
    context = request.get("context", "")

    ensure_initialized()

    if skill_id not in _skills_cache:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills_cache[skill_id]
    content = load_skill_content(skill["path"])

    return {
        "success": True,
        "skill_id": skill_id,
        "name": skill["name"],
        "content": content,
        "context": context,
        "triggers": skill.get("triggers", [])
    }