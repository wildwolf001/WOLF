"""
Skill Tool - 注册为 WOLF 工具，LLM 通过 function calling 调用
参考 cc-haha-main/src/tools/SkillTool/SkillTool.ts
"""
import re
import logging
from typing import Dict, Any

from ..tools.registry import ToolDefinition, ToolResult, tool_registry
from .registry import skill_registry

logger = logging.getLogger(__name__)

SKILL_TOOL_NAME = "Skill"
SKILL_TOOL_DESCRIPTION = (
    "Execute a skill by name. Skills provide specialized capabilities and domain "
    "knowledge for specific tasks. Use when a skill matches the user's request."
)

SKILL_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "skill": {
            "type": "string",
            "description": "The skill name to invoke (e.g., 'scrapling-official', 'commit')"
        },
        "args": {
            "type": "string",
            "description": "Optional arguments to pass to the skill"
        }
    },
    "required": ["skill"]
}


def _substitute_variables(body: str, args: str = "", skill_dir: str = "") -> str:
    """
    Substitute variables in skill body:
    - $ARGUMENTS or {args} → replaced with args string
    - ${CLAUDE_SKILL_DIR} → replaced with skill directory path
    """
    result = body
    if args:
        result = result.replace('$ARGUMENTS', args)
        result = result.replace('{args}', args)
        result = result.replace('$args', args)
    if skill_dir:
        result = result.replace('${CLAUDE_SKILL_DIR}', skill_dir)
    return result


def _extract_allowed_tools(skill) -> list:
    """提取 skill 的 allowed-tools 列表"""
    if not skill.frontmatter.allowed_tools:
        return []
    # 展开通配符 *
    allowed = []
    for pattern in skill.frontmatter.allowed_tools:
        if pattern == '*':
            # 所有工具
            return [t.name for t in tool_registry.list_tools()]
        allowed.append(pattern)
    return allowed


async def execute_skill(args: dict, context: dict) -> ToolResult:
    """
    执行 skill 调用。
    LLM 通过 function calling 调用此函数，
    返回展开的 skill 内容作为消息。
    """
    skill_name = args.get('skill', '')
    skill_args = args.get('args', '')

    if not skill_name:
        return ToolResult(
            tool_call_id=context.get('tool_call_id', ''),
            name=SKILL_TOOL_NAME,
            result=None,
            success=False,
            error="Missing required argument: skill"
        )

    # 查找 skill
    skill = skill_registry.get(skill_name)
    if not skill:
        # 模糊搜索
        all_skills = skill_registry.list_skills()
        matches = [s for s in all_skills if skill_name.lower() in s.name.lower()]
        if matches:
            names = ', '.join(s.name for s in matches[:5])
            return ToolResult(
                tool_call_id=context.get('tool_call_id', ''),
                name=SKILL_TOOL_NAME,
                result=None,
                success=False,
                error=f"Skill '{skill_name}' not found. Did you mean: {names}?"
            )
        available = ', '.join(s.name for s in all_skills[:10])
        return ToolResult(
            tool_call_id=context.get('tool_call_id', ''),
            name=SKILL_TOOL_NAME,
            result=None,
            success=False,
            error=f"Skill '{skill_name}' not found. Available skills: {available}"
        )

    # 检查是否禁止模型调用
    if skill.frontmatter.disable_model_invocation:
        return ToolResult(
            tool_call_id=context.get('tool_call_id', ''),
            name=SKILL_TOOL_NAME,
            result=None,
            success=False,
            error=(
                f"Skill '{skill_name}' cannot be invoked by the model. "
                f"It can only be invoked by users via /{skill_name} slash command."
            )
        )

    # 获取 skill 目录
    import os
    skill_dir = os.path.dirname(skill.source_path)

    # 展开变量
    expanded_body = _substitute_variables(skill.body, skill_args, skill_dir)
    expanded_description = skill.description

    # 提取 allowed tools
    allowed_tools = _extract_allowed_tools(skill)

    # 构建返回结果（skill 展开后的完整内容）
    result_parts = []
    result_parts.append(f"[Skill Loaded: {skill_name}]")
    result_parts.append(f"Skill directory: {skill_dir}")
    if skill.frontmatter.version:
        result_parts.append(f"Version: {skill.frontmatter.version}")
    if allowed_tools:
        result_parts.append(f"Allowed tools: {', '.join(allowed_tools)}")

    # List available reference files so LLM can Read them
    ref_dir = os.path.join(skill_dir, 'references')
    examples_dir = os.path.join(skill_dir, 'examples')
    if os.path.isdir(ref_dir):
        ref_files = []
        for root, dirs, files in os.walk(ref_dir):
            for f in files:
                ref_files.append(os.path.relpath(os.path.join(root, f), skill_dir))
        if ref_files:
            result_parts.append(f"Reference files: {', '.join(ref_files[:10])}{'...' if len(ref_files) > 10 else ''}")
    if os.path.isdir(examples_dir):
        example_files = [f for f in os.listdir(examples_dir) if f.endswith('.py')]
        if example_files:
            result_parts.append(f"Example scripts: {', '.join(example_files)}")

    result_parts.append("")
    result_parts.append("---")
    result_parts.append(f"To read reference files: Read file_path=\"{skill_dir}/references/<filename>\"")
    if os.path.isdir(examples_dir):
        result_parts.append(f"To run examples: Bash command=\"python {skill_dir}/examples/<script>\"")
    result_parts.append("")
    result_parts.append(expanded_body)

    # Return the complete text with header info + body
    full_body = "\n".join(result_parts)

    logger.info(
        f"Skill '{skill_name}' invoked"
        f"{' with args: ' + skill_args if skill_args else ''}"
        f" (source: {skill.source}, body: {len(full_body)} chars)"
    )

    return ToolResult(
        tool_call_id=context.get('tool_call_id', ''),
        name=SKILL_TOOL_NAME,
        result={
            'success': True,
            'skill_name': skill_name,
            'skill_description': expanded_description,
            'skill_body': full_body,
            'skill_source': skill.source,
            'skill_dir': skill_dir,
            'allowed_tools': allowed_tools,
            'status': 'inline',
        },
        success=True
    )


def register_skill_tool():
    """注册 Skill 工具到全局 ToolRegistry"""
    tool_registry.register(ToolDefinition(
        name=SKILL_TOOL_NAME,
        description=SKILL_TOOL_DESCRIPTION,
        input_schema=SKILL_TOOL_SCHEMA,
        function=execute_skill,
        is_read_only=False,  # Skill 可能调用修改性工具
    ))
    logger.info("Skill tool registered")
