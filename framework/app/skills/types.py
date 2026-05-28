"""
Skills Types - 技能类型定义
参考 cc-haha-main/src/skills/ 和 SKILL.md 规范
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SkillFrontmatter:
    """SKILL.md YAML frontmatter 解析结果"""
    name: str
    description: str
    allowed_tools: List[str] = field(default_factory=list)
    when_to_use: Optional[str] = None
    user_invocable: bool = True
    disable_model_invocation: bool = False
    context: str = "inline"  # "inline" or "fork" (fork reserved for future)
    version: Optional[str] = None
    model: Optional[str] = None
    paths: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'allowed_tools': self.allowed_tools,
            'when_to_use': self.when_to_use,
            'user_invocable': self.user_invocable,
            'context': self.context,
            'version': self.version,
        }


@dataclass
class SkillDefinition:
    """完整的 Skill 定义"""
    frontmatter: SkillFrontmatter
    body: str  # Raw markdown body (after frontmatter)
    source_path: str  # Where the SKILL.md was loaded from
    source: str  # "project", "user", "bundled"

    @property
    def name(self) -> str:
        return self.frontmatter.name

    @property
    def description(self) -> str:
        return self.frontmatter.description

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'source': self.source,
            'source_path': self.source_path,
            'body_length': len(self.body),
            **self.frontmatter.to_dict(),
        }
