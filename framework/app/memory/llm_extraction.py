"""
LLM-Driven Memory Extraction Service
使用LLM智能分析对话，提取值得持久化的记忆

替代原有的关键词正则提取 (extraction.py)
"""
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from .types import MemoryEntry, MemoryTypeEnum
from .directory import get_memory_directory, MemoryDirectory


# LLM提取的system prompt
EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction assistant. Your job is to analyze conversations and identify information worth saving as persistent memories.

## Memory Types to Extract

1. **user** — User role, preferences, knowledge level, responsibilities
   Example: "I'm a data scientist investigating logging" → user memory about their role and focus

2. **feedback** — User corrections or confirmations about how to approach work
   Examples: "don't mock the database in tests" → feedback
   "yes exactly, that's the right approach" → feedback (positive confirmation)

3. **project** — Project milestones, deadlines, bugs, incidents, ongoing initiatives
   Examples: "we're freezing merges after Thursday" → project memory
   "the auth rewrite is for compliance reasons" → project context

4. **reference** — Pointers to external systems and resources
   Examples: "pipeline bugs are tracked in Linear project INGEST" → reference
   "the Grafana board at grafana.internal/d/api-latency is for oncall" → reference

## What NOT to Save
- Code patterns, conventions, architecture (derivable from code)
- Git history, recent changes (use git log/blame)
- Debugging solutions (the fix is in the code)
- Anything already documented
- Ephemeral task details, temporary state, current conversation context

## Rules
- Extract ONLY genuinely new information not already found in existing memories
- If nothing new is found, return an empty memories list
- Write a brief session_summary (one sentence, in the language of the conversation)

## Output Format
You MUST respond with ONLY valid JSON, no markdown, no explanation:
{
  "memories": [
    {
      "name": "short_snake_case_name",
      "type": "user|feedback|project|reference",
      "description": "one-line description (~150 chars)",
      "content": "full memory content with context"
    }
  ],
  "session_summary": "A one-line summary of this conversation session"
}
"""


class LLMMemoryExtractionService:
    """
    使用LLM进行记忆提取的服务
    """

    def __init__(self, memory_dir: Optional[str] = None):
        self._memory_dir = get_memory_directory(memory_dir)

    async def extract(
        self,
        session_messages: List[Dict[str, Any]],
        session_id: str = ""
    ) -> List[str]:
        """
        使用LLM分析对话并提取记忆

        Args:
            session_messages: [{"role": "user|assistant", "content": "..."}, ...]
            session_id: 会话ID

        Returns:
            新创建的记忆文件路径列表
        """
        # 1. 获取现有记忆列表（供LLM参考去重）
        existing_names = set()
        try:
            for filepath, entry in self._memory_dir.list_memory_files():
                existing_names.add(entry.name)
                existing_names.add(entry.entry_id)
        except Exception:
            pass

        # 2. 构建LLM消息
        conversation_text = self._format_conversation(session_messages)
        existing_text = "\n".join(f"- {name}" for name in sorted(existing_names)) if existing_names else "(none)"

        user_prompt = f"""## Existing Memory Names (avoid duplicates)
{existing_text}

## Conversation to Analyze
{conversation_text}"""

        # 3. 调用LLM
        try:
            result = await self._call_llm(EXTRACTION_SYSTEM_PROMPT, user_prompt)
            parsed = self._parse_llm_response(result)
        except Exception:
            # LLM调用失败，返回空（调用方可降级到关键词提取）
            return []

        # 4. 保存提取的记忆
        saved_files = []
        for mem_data in parsed.get("memories", []):
            try:
                entry = self._create_memory_entry(mem_data)
                filepath = self._memory_dir.write_memory(entry)
                saved_files.append(filepath)
            except Exception:
                continue

        # 5. 保存会话摘要
        session_summary = parsed.get("session_summary", "")
        if session_summary and session_messages:
            try:
                from datetime import datetime
                safe_id = session_id.replace(":", "_").replace("/", "_").replace("\\", "_")[:32] if session_id else ""
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                summary_entry = MemoryEntry(
                    name=f"session_{ts}" if not safe_id else f"session_{safe_id}_{ts}",
                    description=session_summary[:150],
                    memory_type=MemoryTypeEnum.PROJECT,
                    content=f"# Session Summary\n\n{session_summary}\n\n## Key Topics\n\n"
                )
                filepath = self._memory_dir.write_memory(summary_entry)
                saved_files.append(filepath)
            except Exception:
                pass

        return saved_files

    def extract_keyword_fallback(
        self,
        session_messages: List[Dict[str, Any]]
    ) -> List[str]:
        """
        关键词正则提取（LLM失败时的降级方案）
        """
        from .extraction import get_memory_extraction_service
        import asyncio

        extractor = get_memory_extraction_service()
        saved = asyncio.get_event_loop().run_until_complete(
            extractor.extract_and_save(session_messages)
        ) if asyncio.get_event_loop().is_running() else []

        # If loop is running, can't use run_until_complete
        if not saved:
            return []
        return saved

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """格式化对话为文本"""
        lines = []
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if not content:
                continue
            # 截断过长的消息
            if len(content) > 2000:
                content = content[:2000] + "...[truncated]"
            prefix = {"user": "USER", "assistant": "ASSISTANT", "system": "SYSTEM"}.get(role, role.upper())
            lines.append(f"[{prefix}] {content}")
        return "\n\n".join(lines)

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用LLM，返回文本响应"""
        from ..services.llm_service import LLMService
        from ..core.runtime_config import runtime_config

        llm = LLMService(provider=runtime_config.current_provider)
        result = await llm.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2048,
        )

        if result.get("success") or result.get("content"):
            return result.get("content", "")
        return ""

    def _parse_llm_response(self, text: str) -> Dict[str, Any]:
        """解析LLM返回的JSON"""
        if not text:
            return {"memories": [], "session_summary": ""}

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 代码块
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { ... } 对象
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                pass

        return {"memories": [], "session_summary": ""}

    def _create_memory_entry(self, data: Dict[str, Any]) -> MemoryEntry:
        """从LLM输出创建MemoryEntry"""
        memory_type_str = data.get("type", "reference")
        try:
            memory_type = MemoryTypeEnum(memory_type_str)
        except ValueError:
            memory_type = MemoryTypeEnum.USER

        return MemoryEntry(
            name=data.get("name", f"memory_{datetime.utcnow().strftime('%H%M%S')}"),
            description=data.get("description", "")[:150],
            memory_type=memory_type,
            content=data.get("content", ""),
            why=data.get("why"),
            how_to_apply=data.get("how_to_apply"),
        )


# 全局单例
_llm_extraction_service: Optional[LLMMemoryExtractionService] = None


def get_llm_extraction_service(memory_dir: Optional[str] = None) -> LLMMemoryExtractionService:
    """获取LLM记忆提取服务实例"""
    global _llm_extraction_service
    if _llm_extraction_service is None:
        _llm_extraction_service = LLMMemoryExtractionService(memory_dir)
    return _llm_extraction_service


def reset_llm_extraction() -> None:
    """重置LLM提取服务"""
    global _llm_extraction_service
    _llm_extraction_service = None
