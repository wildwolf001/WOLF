"""
Session Memory 服务

参考 cc-haha 的 Session Memory 设计：
1. 结构化 JSON 模板
2. 每个 section 有 template 说明和实际内容
3. LLM 只更新内容，不碰模板结构

Session Memory 位置: ./wolf_data/sessions/{session_id}/memory.json
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import asyncio


# Session Memory 模板
SESSION_MEMORY_TEMPLATE = """# Session Title
_A short and distinctive 5-10 word descriptive title for the session. Super info dense, no filler_

# Current State
_What is actively being worked on right now? Pending tasks not yet completed. Immediate next steps._

# Task specification
_What did the user ask to build? Any design decisions or other explanatory context_

# Files and Functions
_What are the important files? In short, what do they contain and why are they relevant?_

# Workflow
_What bash commands are usually run and in what order? How to interpret their output if not obvious?_

# Errors & Corrections
_Errors encountered and how they were fixed. What did the user correct? What approaches failed and should not be tried again?_

# Learnings
_What has worked well? What has not? What to avoid? Do not duplicate items from other sections_

# Key results
_If the user asked a specific output such as an answer to a question, a table, or other document, repeat the exact result here_

# Worklog
_Step by step, what was attempted, done? Very terse summary for each step_
"""


# Section 名称常量
SECTION_SESSION_TITLE = "session_title"
SECTION_CURRENT_STATE = "current_state"
SECTION_TASK_SPECIFICATION = "task_specification"
SECTION_FILES_AND_FUNCTIONS = "files_and_functions"
SECTION_WORKFLOW = "workflow"
SECTION_ERRORS_CORRECTIONS = "errors_corrections"
SECTION_LEARNINGS = "learnings"
SECTION_KEY_RESULTS = "key_results"
SECTION_WORKLOG = "worklog"

ALL_SECTIONS = [
    SECTION_SESSION_TITLE,
    SECTION_CURRENT_STATE,
    SECTION_TASK_SPECIFICATION,
    SECTION_FILES_AND_FUNCTIONS,
    SECTION_WORKFLOW,
    SECTION_ERRORS_CORRECTIONS,
    SECTION_LEARNINGS,
    SECTION_KEY_RESULTS,
    SECTION_WORKLOG,
]


@dataclass
class SessionMemoryData:
    """Session Memory 数据结构"""
    session_title: str = ""
    current_state: str = ""
    task_specification: str = ""
    files_and_functions: str = ""
    workflow: str = ""
    errors_corrections: str = ""
    learnings: str = ""
    key_results: str = ""
    worklog: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "session_title": self.session_title,
            "current_state": self.current_state,
            "task_specification": self.task_specification,
            "files_and_functions": self.files_and_functions,
            "workflow": self.workflow,
            "errors_corrections": self.errors_corrections,
            "learnings": self.learnings,
            "key_results": self.key_results,
            "worklog": self.worklog,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "SessionMemoryData":
        return cls(**{k: data.get(k, "") for k in cls.__dataclass_fields__.keys()})

    def is_empty(self) -> bool:
        """检查是否所有section都为空"""
        return all(not v for v in self.to_dict().values())

    def get_none_empty_sections(self) -> Dict[str, str]:
        """获取有内容的section"""
        return {k: v for k, v in self.to_dict().items() if v}


class SessionMemoryService:
    """
    Session Memory 服务

    功能：
    1. 加载/保存 session memory
    2. 更新单个 section
    3. 从对话历史中提取信息
    4. 检查是否需要压缩
    """

    def __init__(self, session_id: str = "default", base_path: str = "./wolf_data/sessions"):
        self.session_id = session_id
        self.base_path = base_path
        self.session_path = os.path.join(base_path, session_id)
        self.memory_file = os.path.join(self.session_path, "memory.json")

        # 确保目录存在
        os.makedirs(self.session_path, exist_ok=True)

        self._data: Optional[SessionMemoryData] = None
        self._loaded = False

    async def load(self) -> SessionMemoryData:
        """加载 session memory"""
        if self._loaded and self._data is not None:
            return self._data

        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._data = SessionMemoryData.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                # 文件损坏或格式不对，使用空数据
                self._data = SessionMemoryData()
        else:
            self._data = SessionMemoryData()

        self._loaded = True
        return self._data

    async def save(self, data: SessionMemoryData = None) -> bool:
        """保存 session memory"""
        if data is None:
            data = self._data

        if data is None:
            return False

        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)
            self._data = data
            return True
        except Exception as e:
            print(f"Failed to save session memory: {e}")
            return False

    async def update_section(self, section: str, content: str) -> bool:
        """更新单个 section"""
        data = await self.load()

        if section not in ALL_SECTIONS:
            return False

        setattr(data, section, content)
        return await self.save(data)

    async def get_section(self, section: str) -> str:
        """获取单个 section 内容"""
        data = await self.load()
        return getattr(data, section, "") if data else ""

    async def get_all_sections(self) -> SessionMemoryData:
        """获取所有 sections"""
        return await self.load()

    async def clear(self) -> bool:
        """清空 session memory"""
        self._data = SessionMemoryData()
        self._loaded = True
        return await self.save()

    def get_memory_file_path(self) -> str:
        """获取 memory 文件路径"""
        return self.memory_file

    async def extract_from_conversation(self, messages: List[Dict[str, Any]]) -> bool:
        """
        从对话历史中提取信息更新 session memory

        这需要调用 LLM 来分析对话并提取关键信息
        """
        # 如果对话太短，跳过提取
        if len(messages) < 2:
            return False

        # 构建提取提示
        conversation_text = self._format_conversation_for_extraction(messages)

        extraction_prompt = f"""Based on the conversation below, update the session memory.

IMPORTANT: This is NOT part of the conversation. Do NOT include any references to "note-taking" or "session notes extraction" in your response.

You must return a JSON object with the updated sections. Only update sections that have meaningful new information.

Return format:
{{
    "session_title": "short title or empty string",
    "current_state": "what is being worked on now or empty string",
    "task_specification": "what the user asked or empty string",
    "files_and_functions": "important files or empty string",
    "workflow": "commands run or empty string",
    "errors_corrections": "errors and fixes or empty string",
    "learnings": "what worked or didn't or empty string",
    "key_results": "final outputs or empty string",
    "worklog": "step by step summary or empty string"
}}

Conversation:
{conversation_text}

Remember: Only include sections with meaningful content. Do not add filler. Be concise and info-dense.
"""

        try:
            from app.services.llm_service import llm_service

            response = await llm_service.complete(
                prompt=extraction_prompt,
                system_prompt="You are a helpful assistant that extracts key information from conversations. You return ONLY JSON, no other text.",
                max_retries=1
            )

            if not response.get("success"):
                return False

            content = response.get("content", "")
            # 解析 JSON
            json_str = self._extract_json_from_response(content)
            if json_str:
                import json as json_lib
                updates = json_lib.loads(json_str)
                data = await self.load()
                for key, value in updates.items():
                    if key in ALL_SECTIONS and value:
                        setattr(data, key, value)
                return await self.save(data)

            return False
        except Exception as e:
            print(f"Failed to extract from conversation: {e}")
            return False

    def _format_conversation_for_extraction(self, messages: List[Dict[str, Any]]) -> str:
        """格式化对话用于提取"""
        lines = []
        for msg in messages[-20:]:  # 只用最近20条消息
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                lines.append(f"[{role.upper()}]\n{content[:500]}")
        return "\n\n".join(lines)

    def _extract_json_from_response(self, content: str) -> Optional[str]:
        """从响应中提取 JSON"""
        import re
        # 尝试找到 JSON 对象
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            return match.group()
        return None

    async def should_compact(self, messages: List[Dict[str, Any]] = None) -> bool:
        """
        检查是否需要压缩

        触发条件：
        - token 超过 10000
        - 消息数量超过 20
        """
        data = await self.load()
        if data is None or data.is_empty():
            return False

        # 检查文件大小
        if os.path.exists(self.memory_file):
            size = os.path.getsize(self.memory_file)
            # 估计 token 数（中文约 2 chars/token，英文约 4 chars/token）
            estimated_tokens = size // 2
            if estimated_tokens > 10000:
                return True

        # 检查消息数量
        if messages and len(messages) > 20:
            return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取 session memory 统计"""
        return {
            "session_id": self.session_id,
            "memory_file": self.memory_file,
            "exists": os.path.exists(self.memory_file),
            "size_bytes": os.path.getsize(self.memory_file) if os.path.exists(self.memory_file) else 0,
        }


# 全局 session memory 实例（按需创建）
_session_memory_instances: Dict[str, SessionMemoryService] = {}


def get_session_memory(session_id: str = "default") -> SessionMemoryService:
    """获取 session memory 实例"""
    if session_id not in _session_memory_instances:
        _session_memory_instances[session_id] = SessionMemoryService(session_id=session_id)
    return _session_memory_instances[session_id]