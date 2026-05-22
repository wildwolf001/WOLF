"""
Compact Service - 自动压缩服务

三级压缩机制：
1. Micro-compact (WorkingMemory 级别) - 当达到限制时自动压缩
2. Session Memory 压缩 - 当超过 10000 tokens 时调用 LLM 提取
3. Long-term Memory 压缩 - 定期清理合并

参考 cc-haha 的 auto-compact 设计
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class CompactService:
    """
    压缩服务 - 管理三级记忆系统的自动压缩

    使用时机：
    1. WorkingMemory 达到容量限制
    2. Session Memory 超过 token 限制
    3. Long-term Memory 需要清理
    """

    # 压缩阈值
    WORKING_MEMORY_MSG_LIMIT = 18  # 保留最近 18 条消息
    WORKING_MEMORY_CHAR_LIMIT = 7000  # 保留最近 7000 字符
    SESSION_MEMORY_TOKEN_LIMIT = 10000  # Session Memory 上限
    LONG_TERM_MEMORY_MAX_ENTRIES = 100  # 每类型最大记忆数

    def __init__(self):
        self._last_compact_time = {}

    # ==================== Working Memory 压缩 ====================

    async def compact_working_memory(self, working_memory) -> Dict[str, Any]:
        """
        Micro-compact: 压缩 WorkingMemory

        策略：
        1. 保留最近的 N 条消息
        2. 如果有工具结果，优先保留（重要上下文）
        3. 截断超长消息

        Returns:
            压缩统计信息
        """
        if working_memory is None:
            return {"compacted": False, "reason": "no working_memory"}

        original_count = len(working_memory.messages)
        original_chars = sum(len(m.content) for m in working_memory.messages)

        # 检查是否需要压缩
        if original_count < self.WORKING_MEMORY_MSG_LIMIT and original_chars < self.WORKING_MEMORY_CHAR_LIMIT:
            return {"compacted": False, "reason": "under threshold"}

        # 优先保留工具结果消息
        tool_result_msgs = [
            m for m in working_memory.messages
            if "[Tool Result" in m.content
        ]

        # 其他消息只保留最近的
        other_msgs = [
            m for m in working_memory.messages
            if "[Tool Result" not in m.content
        ]
        other_msgs = other_msgs[-self.WORKING_MEMORY_MSG_LIMIT:]

        # 合并并截断
        kept_msgs = tool_result_msgs + other_msgs
        kept_msgs = kept_msgs[-self.WORKING_MEMORY_MSG_LIMIT:]

        # 截断超长消息
        truncated_msgs = []
        current_chars = 0
        for msg in reversed(kept_msgs):
            msg_len = len(msg.content)
            if current_chars + msg_len <= self.WORKING_MEMORY_CHAR_LIMIT:
                truncated_msgs.insert(0, msg)
                current_chars += msg_len
            else:
                # 截断此消息
                remaining = self.WORKING_MEMORY_CHAR_LIMIT - current_chars
                if remaining > 100:
                    truncated_content = msg.content[:remaining] + "... [truncated]"
                    from app.agents.working_memory import Message
                    truncated_msgs.insert(0, Message(role=msg.role, content=truncated_content))
                break

        working_memory.messages = truncated_msgs

        return {
            "compacted": True,
            "reason": "working_memory_limit",
            "original_count": original_count,
            "new_count": len(truncated_msgs),
            "original_chars": original_chars,
            "new_chars": current_chars
        }

    # ==================== Session Memory 压缩 ====================

    async def compact_session_memory(self, session_memory, llm_service=None) -> Dict[str, Any]:
        """
        Session Memory 压缩

        当 Session Memory 超过限制时：
        1. 调用 LLM 提取关键信息
        2. 重写 session memory 内容

        Args:
            session_memory: SessionMemoryService 实例
            llm_service: LLM 服务实例（用于调用 LLM）

        Returns:
            压缩统计信息
        """
        if session_memory is None:
            return {"compacted": False, "reason": "no session_memory"}

        # 检查是否需要压缩
        if not await session_memory.should_compact():
            return {"compacted": False, "reason": "under threshold"}

        # 加载当前 session memory
        data = await session_memory.load()
        if data is None or data.is_empty():
            return {"compacted": False, "reason": "empty"}

        # 调用 LLM 提取关键信息
        if llm_service:
            extracted = await self._extract_with_llm(data, llm_service)
            if extracted:
                # 更新 session memory
                for key, value in extracted.items():
                    if key in data.to_dict() and value:
                        setattr(data, key, value)
                await session_memory.save(data)
                return {
                    "compacted": True,
                    "reason": "llm_extraction",
                    "extracted_keys": list(extracted.keys())
                }

        # 回退方案：简单截断
        return await self._simple_compact_session(session_memory, data)

    async def _extract_with_llm(self, session_data, llm_service) -> Optional[Dict[str, str]]:
        """使用 LLM 从 session memory 中提取关键信息"""
        prompt = f"""You are a helpful assistant that extracts key information from session memory.

Current session memory:
{json.dumps(session_data.to_dict(), ensure_ascii=False, indent=2)}

Extract the most important information that should be preserved for future sessions.
Focus on:
- What task is being worked on
- Key files and functions involved
- Workflow and commands used
- Errors encountered and how they were fixed
- Key learnings

Return a JSON object with updated session memory sections. Only include meaningful content.
Return format:
{{
    "session_title": "...",
    "current_state": "...",
    "task_specification": "...",
    "files_and_functions": "...",
    "workflow": "...",
    "errors_corrections": "...",
    "learnings": "...",
    "key_results": "...",
    "worklog": "..."
}}
"""

        try:
            response = await llm_service.complete(
                prompt=prompt,
                system_prompt="You are a helpful assistant. Return ONLY JSON, no other text.",
                max_retries=1
            )
            if response.get("success"):
                content = response.get("content", "")
                # 提取 JSON
                match = json.search(r'\{[\s\S]*\}', content)
                if match:
                    return json.loads(match.group())
        except Exception as e:
            print(f"LLM extraction failed: {e}")

        return None

    async def _simple_compact_session(self, session_memory, data) -> Dict[str, Any]:
        """简单压缩 session memory - 截断过长的 section"""
        # 截断每个 section 到 500 字符
        truncated = {}
        for key, value in data.to_dict().items():
            if isinstance(value, str) and len(value) > 500:
                truncated[key] = value[:500] + "... [truncated]"
            else:
                truncated[key] = value

        # 创建新的 session data
        from app.agents.session_memory import SessionMemoryData
        new_data = SessionMemoryData.from_dict(truncated)
        await session_memory.save(new_data)

        return {
            "compacted": True,
            "reason": "simple_truncate",
            "original_size": sum(len(v) for v in data.to_dict().values()),
            "new_size": sum(len(v) for v in truncated.values())
        }

    # ==================== Long-term Memory 压缩 ====================

    async def compact_long_term_memory(self, long_term_memory) -> Dict[str, Any]:
        """
        Long-term Memory 压缩

        清理策略：
        1. 删除超过 90 天的记忆
        2. 合并相似的记忆
        3. 删除低价值记忆（长时间未访问）

        Args:
            long_term_memory: LongTermMemoryService 实例

        Returns:
            压缩统计信息
        """
        if long_term_memory is None:
            return {"compacted": False, "reason": "no long_term_memory"}

        deleted_count = 0
        from datetime import datetime, timedelta

        for memory_type in ["user", "project", "feedback", "reference"]:
            memories = await long_term_memory.list_memories(memory_type=memory_type)
            for mem in memories:
                # 删除超过 90 天的记忆
                if mem.last_accessed:
                    try:
                        last_access = datetime.fromisoformat(mem.last_accessed)
                        if datetime.now() - last_access > timedelta(days=90):
                            await long_term_memory.delete_memory(mem.name, memory_type)
                            deleted_count += 1
                    except Exception:
                        pass

        return {
            "compacted": True,
            "reason": "long_term_cleanup",
            "deleted_count": deleted_count
        }

    # ==================== 统计信息 ====================

    def get_compact_stats(self, working_memory=None, session_memory=None, long_term_memory=None) -> Dict[str, Any]:
        """获取压缩统计信息"""
        stats = {
            "working_memory": {},
            "session_memory": {},
            "long_term_memory": {}
        }

        if working_memory:
            stats["working_memory"] = working_memory.get_stats()

        if session_memory:
            stats["session_memory"] = session_memory.get_stats()

        if long_term_memory:
            stats["long_term_memory"] = long_term_memory.get_stats()

        return stats


# 全局实例
_compact_service_instance: Optional[CompactService] = None


def get_compact_service() -> CompactService:
    """获取压缩服务实例"""
    global _compact_service_instance
    if _compact_service_instance is None:
        _compact_service_instance = CompactService()
    return _compact_service_instance