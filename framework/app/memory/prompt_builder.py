"""
Memory Prompt Builder
参考 cc-haha-main/src/memdir/memdir.ts - buildMemoryLines()

将记忆系统的行为指导注入到系统提示中
"""

from typing import Optional, List

from .types import (
    MemoryTypeEnum,
    MEMORY_TYPE_SPECS,
    WHAT_NOT_TO_SAVE,
    WHAT_NOT_TO_SAVE_RULE,
    WHEN_TO_ACCESS_MEMORIES,
    MEMORY_DRIFT_CAVEAT,
    TRUSTING_RECALL_SECTION,
    MEMORY_FRONTMATTER_EXAMPLE,
    ENTRYPOINT_NAME,
    MAX_ENTRYPOINT_LINES,
)
from .directory import get_memory_directory, DEFAULT_MEMORY_DIR


class MemoryPromptBuilder:
    """构建记忆系统的系统提示部分"""

    def __init__(self, memory_dir: Optional[str] = None):
        self._memory_dir = memory_dir or DEFAULT_MEMORY_DIR
        self._dir = get_memory_directory(self._memory_dir)

    @property
    def memory_dir(self) -> 'MemoryDirectory':
        return self._dir

    def build_memory_lines(self, display_name: str = 'auto memory') -> List[str]:
        """构建记忆行为指导行 (不含 MEMORY.md 内容)"""
        how_to_save = [
            '## How to save memories',
            '',
            'Saving a memory is a two-step process:',
            '',
            '**Step 1** — write the memory to its own file (e.g., `user_role.md`, `feedback_testing.md`) using this frontmatter format:',
            '',
            MEMORY_FRONTMATTER_EXAMPLE,
            '',
            f'**Step 2** — add a pointer to that file in `{ENTRYPOINT_NAME}`. `{ENTRYPOINT_NAME}` is an index, not a memory — each entry should be one line, under ~150 characters: `- [Title](file.md) — one-line hook`.',
            '',
            f'- `{ENTRYPOINT_NAME}` is always loaded — lines after {MAX_ENTRYPOINT_LINES} will be truncated',
            '- Keep the name, description, and type fields in memory files up-to-date',
            '- Organize memory semantically by topic, not chronologically',
            '- Do not write duplicate memories.',
        ]

        lines = [
            f"# {display_name}",
            '',
            f"You have a persistent, file-based memory system at `{self._dir.path}`. This directory already exists — write to it directly with the Write tool.",
            '',
            "You should build up this memory system over time so that future conversations can have a complete picture of who the user is, how they'd like to collaborate with you, what behaviors to avoid or repeat.",
            '',
            'If the user explicitly asks you to remember something, save it immediately as whichever type fits best. If they ask you to forget something, find and remove the relevant entry.',
            '',
        ]

        lines.extend(self._build_types_section())
        lines.extend([''])

        lines.extend([
            '## What NOT to save in memory',
            '',
            *WHAT_NOT_TO_SAVE,
            WHAT_NOT_TO_SAVE_RULE,
            '',
        ])

        lines.extend(how_to_save)
        lines.extend([''])

        lines.extend([
            '## When to access memories',
            '',
            *WHEN_TO_ACCESS_MEMORIES,
            MEMORY_DRIFT_CAVEAT,
            '',
        ])

        lines.extend(TRUSTING_RECALL_SECTION)
        lines.extend([''])

        lines.extend([
            '## Memory and other forms of persistence',
            'Memory is one of several persistence mechanisms. Memory can be recalled in future conversations and should not be used for persisting information that is only useful within the current conversation.',
            '- When to use or update a plan instead of memory: If you are about to start a non-trivial implementation task and you would like to reach alignment with the user on your approach you should use a Plan rather than saving to memory.',
            '- When to use or update tasks instead of memory: When you need to break your work in current conversation into discrete steps or keep track of your progress use tasks instead of saving to memory.',
            '',
        ])

        return lines

    def _build_types_section(self) -> List[str]:
        """构建4类型分类说明"""
        lines = ['## Types of memory', '', '<types>']

        for memory_type in [MemoryTypeEnum.USER, MemoryTypeEnum.FEEDBACK,
                           MemoryTypeEnum.PROJECT, MemoryTypeEnum.REFERENCE]:
            spec = MEMORY_TYPE_SPECS[memory_type]
            lines.extend([
                '<type>',
                f'    <name>{memory_type.value}</name>',
                f'    <description>{spec["description"]}</description>',
                f'    <when_to_save>{spec["when_to_save"]}</when_to_save>',
                f'    <how_to_use>{spec["how_to_use"]}</how_to_use>',
                '</type>',
                '',
            ])

        lines.append('</types>')
        return lines

    def build_system_prompt_addition(self) -> str:
        """构建要追加到系统提示的记忆部分"""
        return '\n'.join(self.build_memory_lines())


_memory_prompt_builder: Optional[MemoryPromptBuilder] = None


def get_memory_prompt_builder(memory_dir: Optional[str] = None) -> MemoryPromptBuilder:
    global _memory_prompt_builder
    if _memory_prompt_builder is None:
        _memory_prompt_builder = MemoryPromptBuilder(memory_dir)
    return _memory_prompt_builder


def build_memory_system_prompt(memory_dir: Optional[str] = None) -> str:
    """构建记忆系统提示 = 行为指导 + MEMORY.md 实际内容"""
    builder = get_memory_prompt_builder(memory_dir)

    # 构建行为指导
    lines = builder.build_memory_lines()

    # 读取 MEMORY.md 实际内容并追加
    memory_dir_instance = get_memory_directory(memory_dir)
    entrypoint_content = memory_dir_instance.read_entrypoint()

    lines.extend(['', f'## {ENTRYPOINT_NAME}', ''])

    if entrypoint_content.strip():
        lines.append(entrypoint_content)
    else:
        lines.append(f'Your {ENTRYPOINT_NAME} is currently empty.')

    return '\n'.join(lines)