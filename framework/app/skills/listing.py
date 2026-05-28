"""
Skills Listing - 格式化 skills 列表用于注入 system prompt
参考 cc-haha-main/src/utils/attachments.ts getSkillListingAttachments()
"""
from typing import List

from .types import SkillDefinition
from .registry import skill_registry


MAX_DESC_LENGTH = 250  # 每个 skill 描述的最大字符数


def format_skill_for_prompt(skill: SkillDefinition) -> str:
    """格式化单个 skill 为 prompt 条目"""
    desc = skill.description or skill.frontmatter.description or ''
    if len(desc) > MAX_DESC_LENGTH:
        desc = desc[:MAX_DESC_LENGTH - 3] + '...'
    source_tag = f" ({skill.source})" if skill.source else ""
    return f"- {skill.name}{source_tag}: {desc}"


def get_skills_listing(max_skills: int = 50) -> str:
    """
    生成 skill 列表文本，用于注入 system prompt。
    类似 cc-haha 的 skill_listing attachment。
    """
    skills = skill_registry.list_invocable()
    if not skills:
        return ""

    lines: List[str] = []
    lines.append("The following skills are available for use with the Skill tool:")

    for i, skill in enumerate(skills[:max_skills]):
        lines.append(format_skill_for_prompt(skill))

    if len(skills) > max_skills:
        lines.append(f"... and {len(skills) - max_skills} more skills")

    return "\n".join(lines)


def get_skills_section(max_skills: int = 50) -> str:
    """
    生成完整的 skills section，带 system-reminder 标签。
    注入到系统提示词中。
    """
    listing = get_skills_listing(max_skills)
    if not listing:
        return ""

    return f"""<system-reminder>
{listing}

- /<skill-name> is shorthand for users to invoke a user-invocable skill. When executed, the skill gets expanded to a full prompt. Use the Skill tool to execute them. IMPORTANT: Only use Skill for skills listed in its user-invocable skills section - do not guess or use built-in CLI commands.
</system-reminder>"""


def get_skill_tool_guidance() -> str:
    """
    Skill tool 的使用指南，注入到 system prompt 中作为工具使用说明。
    参考 cc-haha 的 SkillTool.prompt()
    """
    if not skill_registry.list_invocable():
        return ""

    user_invocable = [
        s.name for s in skill_registry.list_skills()
        if s.frontmatter.user_invocable
    ]

    guidance = """When users ask you to perform tasks, check if any of the available skills match. Skills provide specialized capabilities and domain knowledge.

When users reference a "slash command" or "/<something>" (e.g., "/commit", "/review-pr"), they are referring to a skill. Use the Skill tool to execute them.

How to invoke:
- Use the Skill tool with the skill name and optional arguments
- Examples:
  - Skill(skill="commit", args="-m 'Fix bug'")
  - Skill(skill="scrapling-official")

Important:
- Available skills are listed in system-reminder messages in the conversation
- When a skill matches the user's request, this is a BLOCKING REQUIREMENT: invoke the relevant Skill tool BEFORE generating any other response about the task
- NEVER mention a skill without actually calling the Skill tool
"""

    if user_invocable:
        names = ', '.join(f'/{s}' for s in sorted(user_invocable))
        guidance += f"\nUser-invocable skills: {names}"

    return guidance
