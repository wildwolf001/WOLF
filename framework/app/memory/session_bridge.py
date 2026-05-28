"""
Session Memory Bridge
将会话记忆桥接到持久化记忆系统
"""
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from .types import MemoryEntry, MemoryTypeEnum
from .directory import get_memory_directory, MemoryDirectory


class SessionBridgeService:
    """
    桥接 SessionMemory ↔ Persistent Memory
    """

    def __init__(self, memory_dir: Optional[str] = None):
        self._memory_dir = get_memory_directory(memory_dir)

    def save_session_context(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        summary: str = ""
    ) -> Optional[str]:
        """
        将当前会话的关键上下文保存到持久记忆

        Returns:
            保存的文件路径，如果无事可存则返回None
        """
        # 提取用户消息中的关键信息
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return None

        # 收集用户线索
        first_user_msg = user_messages[0].get("content", "")[:500]
        last_user_msg = user_messages[-1].get("content", "")[:500]

        # 如果对话很短（单条消息且<50字符），不保存
        if len(user_messages) == 1 and len(first_user_msg) < 50:
            return None

        # 生成会话上下文记忆
        safe_id = session_id.replace(":", "_").replace("/", "_").replace("\\", "_")[:32]
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        content_lines = [
            f"# Session Context: {ts}",
            f"Session ID: {session_id}",
            f"Messages: {len(messages)} total ({len(user_messages)} user, {len(messages) - len(user_messages)} assistant)",
            "",
            "## First User Message",
            first_user_msg,
        ]

        if last_user_msg != first_user_msg:
            content_lines.extend([
                "",
                "## Last User Message",
                last_user_msg,
            ])

        if summary:
            content_lines.extend([
                "",
                "## Summary",
                summary,
            ])

        entry = MemoryEntry(
            name=f"session_ctx_{safe_id}_{ts}",
            description=f"Session context: {first_user_msg[:100]}..." if len(first_user_msg) > 100 else f"Session context: {first_user_msg}",
            memory_type=MemoryTypeEnum.PROJECT,
            content="\n".join(content_lines),
        )

        try:
            filepath = self._memory_dir.write_memory(entry)
            return filepath
        except Exception:
            return None

    def get_session_snapshots(self, limit: int = 10) -> List[MemoryEntry]:
        """获取最近的会话快照"""
        all_entries = []
        try:
            for filepath, entry in self._memory_dir.list_memory_files():
                if entry.name.startswith("session_"):
                    all_entries.append(entry)
        except Exception:
            return []

        # 按创建时间排序，返回最近N个
        all_entries.sort(key=lambda e: e.created_at if e.created_at else datetime.min, reverse=True)
        return all_entries[:limit]

    def find_relevant_memories(
        self,
        query: str,
        max_results: int = 5
    ) -> List[MemoryEntry]:
        """
        根据查询找到最相关的持久记忆 (TF-based relevance)
        """
        all_entries = []
        try:
            for filepath, entry in self._memory_dir.list_memory_files():
                # 跳过会话快照（相关性查询针对长期记忆）
                if entry.name.startswith("session_"):
                    continue
                all_entries.append(entry)
        except Exception:
            return []

        if not all_entries:
            return []

        # TF-based relevance scoring
        query_terms = set(self._tokenize(query))
        if not query_terms:
            return all_entries[:max_results]

        scored = []
        for entry in all_entries:
            text = f"{entry.name} {entry.description} {entry.content[:1000]}"
            text_terms = self._tokenize(text)
            if not text_terms:
                continue
            # Simple Jaccard-like score: intersection / union
            intersection = query_terms & text_terms
            union = query_terms | text_terms
            score = len(intersection) / len(union) if union else 0

            # Boost by recency
            if entry.updated_at:
                days_old = (datetime.utcnow() - entry.updated_at).days
                recency_boost = max(0, 1.0 - days_old / 30.0) * 0.2  # up to 0.2 boost
                score += recency_boost

            # Boost by usage
            score += min(entry.usage_count * 0.05, 0.3)  # up to 0.3 boost

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:max_results]]

    def _tokenize(self, text: str) -> set:
        """简易分词"""
        import re
        # 中英文混合分词
        tokens = set()
        # 英文单词
        tokens.update(w.lower() for w in re.findall(r'[a-zA-Z]{2,}', text))
        # 中文双字组合
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        for i in range(len(chinese_chars) - 1):
            tokens.add(chinese_chars[i] + chinese_chars[i + 1])
        return tokens


# 全局单例
_session_bridge: Optional[SessionBridgeService] = None


def get_session_bridge(memory_dir: Optional[str] = None) -> SessionBridgeService:
    """获取会话桥接服务实例"""
    global _session_bridge
    if _session_bridge is None:
        _session_bridge = SessionBridgeService(memory_dir)
    return _session_bridge


def reset_session_bridge() -> None:
    """重置会话桥接"""
    global _session_bridge
    _session_bridge = None
