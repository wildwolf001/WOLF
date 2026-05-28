"""
上下文压缩 Prompt 子系统 — 对标 CC services/compact/prompt.ts
CompactManager：检测上下文使用率 >80% → 触发压缩
"""
from typing import List, Dict
from .core.constants import COMPACTION_THRESHOLD, MAX_RECENT_TURNS, MAX_PINNED_FILES
from .core.schemas import CompactConfig


COMPACTION_SYSTEM_PROMPT = """You are summarizing a conversation that has reached its context limit.
Your goal is to preserve ALL critical information while removing redundant content.

KEEP (high priority):
- Architectural decisions and their rationale
- Unresolved bugs, errors, and their current status
- Implementation details that affect future work
- User preferences and explicit instructions
- File paths that were modified and why

DISCARD (low priority):
- Redundant tool outputs (especially successful ones)
- Intermediate exploration that led nowhere
- Verbose error traces (keep only the key error message)
- Repeated information across multiple turns

OUTPUT FORMAT:
## Current Task State
(summary of what the user asked and current progress)

## Key Decisions Made
(list each decision and WHY it was made)

## Files Modified
(list each file path and what was changed)

## Unresolved Issues
(any bugs, errors, or pending questions)

## User Preferences Noted
(any preferences the user explicitly stated)"""


class CompactManager:
    """上下文压缩管理器"""

    def __init__(self, config: CompactConfig = None):
        self.config = config or CompactConfig()
        self._compact_count = 0

    def should_compact(self, current_tokens: int, max_tokens: int) -> bool:
        """检查是否需要压缩"""
        if max_tokens <= 0:
            return False
        return (current_tokens / max_tokens) > self.config.threshold

    def get_compaction_messages(self, conversation: List[Dict]) -> List[Dict]:
        """生成压缩请求消息"""
        # 保留最近 N 轮
        recent = conversation[-self.config.keep_recent_turns:] if len(conversation) > self.config.keep_recent_turns else conversation
        to_compress = conversation[:-self.config.keep_recent_turns] if len(conversation) > self.config.keep_recent_turns else []

        if not to_compress:
            return [{"role": "system", "content": COMPACTION_SYSTEM_PROMPT}]

        # 构建压缩输入
        compress_text = "\n\n".join(
            f"[{m.get('role', '?')}]: {str(m.get('content', ''))[:500]}"
            for m in to_compress[-50:]  # 最多压缩最近 50 条消息
        )

        return [
            {"role": "system", "content": COMPACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Summarize this conversation:\n\n{compress_text}"}
        ]

    def compact(self, conversation: List[Dict]) -> dict:
        """执行压缩 → 返回压缩结果 + 保留的最近消息"""
        self._compact_count += 1
        recent = conversation[-self.config.keep_recent_turns:] if len(conversation) > self.config.keep_recent_turns else conversation
        return {
            "compact_count": self._compact_count,
            "original_turns": len(conversation),
            "kept_turns": len(recent),
            "messages": self.get_compaction_messages(conversation),
        }
