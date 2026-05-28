"""
Memory Type Taxonomy
参考 cc-haha-main/src/memdir/memoryTypes.ts

记忆被限制为四种类型，捕捉从当前项目状态不可推导的上下文。
可从代码、架构、git历史推导的内容不应被保存为记忆。
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

# ============================================================================
# 类型定义
# ============================================================================

MEMORY_TYPES = ['user', 'feedback', 'project', 'reference']
MemoryType = str


class MemoryTypeEnum(str, Enum):
    """记忆类型枚举 - 对应 CC 的 MemoryType"""
    USER = 'user'
    FEEDBACK = 'feedback'
    PROJECT = 'project'
    REFERENCE = 'reference'

    @classmethod
    def from_string(cls, value: str) -> 'MemoryTypeEnum':
        try:
            return cls(value)
        except ValueError:
            return cls.USER


def parse_memory_type(raw: any) -> Optional[MemoryTypeEnum]:
    """解析原始 frontmatter 值为 MemoryType"""
    if not isinstance(raw, str):
        return None
    try:
        return MemoryTypeEnum(raw)
    except ValueError:
        return None


# ============================================================================
# 记忆项结构
# ============================================================================

@dataclass
class MemoryEntry:
    """单条记忆项"""
    name: str
    description: str
    memory_type: MemoryTypeEnum
    content: str
    why: Optional[str] = None
    how_to_apply: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    usage_count: int = 0
    last_used_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    @property
    def entry_id(self) -> str:
        """基于类型和名称生成的唯一ID（用作filename基础）"""
        safe = self.name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
        safe = ''.join(c for c in safe if c.isalnum() or c in '_-')[:50]
        return f"{self.memory_type.value}_{safe}"

    @property
    def filename(self) -> str:
        return f"{self.entry_id}.md"

    def to_dict(self) -> dict:
        return {
            'id': self.entry_id,
            'name': self.name,
            'description': self.description,
            'type': self.memory_type.value,
            'content': self.content,
            'why': self.why,
            'howToApply': self.how_to_apply,
            'createdAt': int(self.created_at.timestamp() * 1000) if self.created_at else None,
            'updatedAt': int(self.updated_at.timestamp() * 1000) if self.updated_at else None,
            'lastUsedAt': int(self.last_used_at.timestamp() * 1000) if self.last_used_at else None,
            'usageCount': self.usage_count,
        }

    def to_frontmatter(self) -> str:
        lines = [
            "---",
            f"name: {self.name}",
            f"description: {self.description}",
            f"type: {self.memory_type.value}",
        ]
        if self.why:
            lines.append(f"why: {self.why}")
        if self.how_to_apply:
            lines.append(f"howToApply: {self.how_to_apply}")
        lines.append("---")
        lines.append("")
        lines.append(self.content)
        return "\n".join(lines)

    @staticmethod
    def from_frontmatter(content: str) -> Optional['MemoryEntry']:
        import re
        match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
        if not match:
            return None

        frontmatter_str, body = match.groups()
        data = {}
        for line in frontmatter_str.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip().strip('"').strip("'")

        memory_type = parse_memory_type(data.get('type'))
        if not memory_type:
            return None

        return MemoryEntry(
            name=data.get('name', ''),
            description=data.get('description', ''),
            memory_type=memory_type,
            content=body.strip(),
            why=data.get('why'),
            how_to_apply=data.get('howToApply'),
        )


# ============================================================================
# 各类型详细说明
# ============================================================================

MEMORY_TYPE_SPECS = {
    MemoryTypeEnum.USER: {
        'scope': 'always private',
        'description': (
            'Contain information about the user\'s role, goals, responsibilities, '
            'and knowledge. Great user memories help you tailor your future behavior '
            'to the user\'s preferences and perspective.'
        ),
        'when_to_save': 'When you learn any details about the user\'s role, preferences, responsibilities, or knowledge',
        'how_to_use': 'When your work should be informed by the user\'s profile or perspective.',
    },
    MemoryTypeEnum.FEEDBACK: {
        'scope': 'default to private. team only when guidance is project-wide convention',
        'description': (
            'Guidance the user has given you about how to approach work — both what '
            'to avoid and what to keep doing. Record from failure AND success.'
        ),
        'when_to_save': (
            'Any time the user corrects your approach ("no not that", "don\'t", "stop doing X") '
            'OR confirms a non-obvious approach worked ("yes exactly", "perfect")'
        ),
        'how_to_use': 'Let these memories guide your behavior so that the user does not need to offer the same guidance twice.',
        'body_structure': 'Lead with the rule itself, then a **Why:** line and a **How to apply:** line',
    },
    MemoryTypeEnum.PROJECT: {
        'scope': 'private or team, but strongly bias toward team',
        'description': 'Information that you learn about ongoing work, goals, initiatives, bugs, or incidents within the project.',
        'when_to_save': 'When you learn who is doing what, why, or by when. Always convert relative dates to absolute dates.',
        'how_to_use': 'Use these memories to more fully understand the details and nuance behind the user\'s request.',
    },
    MemoryTypeEnum.REFERENCE: {
        'scope': 'usually team',
        'description': 'Stores pointers to where information can be found in external systems.',
        'when_to_save': 'When you learn about resources in external systems and their purpose.',
        'how_to_use': 'When the user references an external system or information that may be in an external system.',
    },
}


# ============================================================================
# What NOT to save
# ============================================================================

WHAT_NOT_TO_SAVE = [
    '- Code patterns, conventions, architecture, file paths, or project structure — these can be derived by reading the current project state.',
    '- Git history, recent changes, or who-changed-what — `git log` / `git blame` are authoritative.',
    '- Debugging solutions or fix recipes — the fix is in the code; the commit message has the context.',
    '- Anything already documented in CLAUDE.md files.',
    '- Ephemeral task details: in-progress work, temporary state, current conversation context.',
]

WHAT_NOT_TO_SAVE_RULE = (
    'These exclusions apply even when the user explicitly asks you to save. '
    'If they ask you to save a PR list or activity summary, ask what was *surprising* '
    'or *non-obvious* about it — that is the part worth keeping.'
)


# ============================================================================
# 访问记忆的指导
# ============================================================================

WHEN_TO_ACCESS_MEMORIES = [
    '- When memories seem relevant, or the user references prior-conversation work.',
    '- You MUST access memory when the user explicitly asks you to check, recall, or remember.',
    '- If the user says to *ignore* or *not use* memory: proceed as if MEMORY.md were empty. Do not apply remembered facts, cite, compare against, or mention memory content.',
]

MEMORY_DRIFT_CAVEAT = (
    'Memory records can become stale over time. Use memory as context for what was true '
    'at a given point in time. Before answering the user or building assumptions based '
    'solely on information in memory records, verify that the memory is still correct '
    'and up-to-date by reading the current state of the files or resources.'
)


TRUSTING_RECALL_SECTION = [
    '## Before recommending from memory',
    '',
    'A memory that names a specific function, file, or flag is a claim that it existed '
    '*when the memory was written*. It may have been renamed, removed, or never merged. Before recommending it:',
    '',
    '- If the memory names a file path: check the file exists.',
    '- If the memory names a function or flag: grep for it.',
    '- If the user is about to act on your recommendation (not just asking about history), verify first.',
    '',
    '"The memory says X exists" is not the same as "X exists now."',
]


MEMORY_FRONTMATTER_EXAMPLE = """```markdown
---
name: {{memory name}}
description: {{one-line description — used to decide relevance in future conversations, so be specific}}
type: {{user, feedback, project, reference}}
---

{{memory content — for feedback/project types, structure as: rule/fact, then **Why:** and **How to apply:** lines}}
```"""


# ============================================================================
# 常量
# ============================================================================

ENTRYPOINT_NAME = 'MEMORY.md'
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000