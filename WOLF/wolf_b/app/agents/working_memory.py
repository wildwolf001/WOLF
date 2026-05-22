"""
Working Memory 模块

参考 cc-haha 的消息管理和 Session Memory 设计：
1. WorkingMemory - 当前对话的工作内存
2. 容量限制：20条消息、5个工具结果、总字符8000

工作内存的三层：
- messages[]: 当前对话历史
- tool_results[]: 工具结果历史
- pending_tool_calls[]: 待执行的工具调用
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Message:
    """消息结构"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""
    tool_calls: List[Dict] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
            tool_calls=data.get("tool_calls", []),
            tool_results=data.get("tool_results", [])
        )


@dataclass
class ToolResult:
    """工具结果结构"""
    tool_name: str
    arguments: Dict[str, Any]
    result: str
    timestamp: str = ""
    success: bool = True

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "timestamp": self.timestamp,
            "success": self.success
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ToolResult":
        return cls(
            tool_name=data.get("tool_name", ""),
            arguments=data.get("arguments", {}),
            result=data.get("result", ""),
            timestamp=data.get("timestamp", ""),
            success=data.get("success", True)
        )

    def get_summary(self, max_length: int = 200) -> str:
        """获取结果摘要"""
        if len(self.result) <= max_length:
            return self.result
        return self.result[:max_length] + f"... [truncated, total {len(self.result)} chars]"


class WorkingMemory:
    """
    工作内存 - 管理当前对话的上下文

    参考 cc-haha 的消息管理策略：
    - 限制消息数量（MAX_MESSAGES = 20）
    - 限制工具结果数量（MAX_TOOL_RESULTS = 5）
    - 限制总字符数（MAX_TOTAL_CHARS = 8000）
    - 自动截断旧消息，保留关键信息
    """

    # 容量限制
    MAX_MESSAGES = 20
    MAX_TOOL_RESULTS = 5
    MAX_TOTAL_CHARS = 8000
    MAX_CONTENT_LENGTH = 2000  # 单条消息最大长度

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.messages: List[Message] = []
        self.tool_results: List[ToolResult] = []
        self.pending_tool_calls: List[Dict] = []
        self._created_at = datetime.now().isoformat()

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        # 压缩过长内容
        if len(content) > self.MAX_CONTENT_LENGTH:
            content = content[:self.MAX_CONTENT_LENGTH] + f"... [truncated, total {len(content)} chars]"

        message = Message(role="user", content=content)
        self.messages.append(message)
        self._enforce_limits()

    def add_assistant_message(self, content: str, tool_calls: List[Dict] = None) -> None:
        """添加助手消息"""
        # 压缩过长内容
        if len(content) > self.MAX_CONTENT_LENGTH:
            content = content[:self.MAX_CONTENT_LENGTH] + f"... [truncated, total {len(content)} chars]"

        message = Message(
            role="assistant",
            content=content,
            tool_calls=tool_calls or []
        )
        self.messages.append(message)
        self._enforce_limits()

    def add_tool_result(self, tool_name: str, arguments: Dict, result: str, success: bool = True) -> None:
        """添加工具结果"""
        tool_result = ToolResult(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success
        )
        self.tool_results.append(tool_result)

        # 限制工具结果数量
        while len(self.tool_results) > self.MAX_TOOL_RESULTS:
            self.tool_results.pop(0)

    def add_pending_tool_calls(self, tool_calls: List[Dict]) -> None:
        """添加待执行的工具调用"""
        self.pending_tool_calls.extend(tool_calls)

    def clear_pending_tool_calls(self) -> None:
        """清空待执行的工具调用"""
        self.pending_tool_calls = []

    def pop_pending_tool_call(self) -> Optional[Dict]:
        """弹出一个待执行的工具调用"""
        if self.pending_tool_calls:
            return self.pending_tool_calls.pop(0)
        return None

    def get_context_for_llm(self) -> List[Dict[str, Any]]:
        """
        获取发送给 LLM 的上下文

        格式：
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "[Tool Result for xxx]\n..."},
            ...
        ]
        """
        result = []

        # 添加消息历史（跳过system，system单独传递）
        for msg in self.messages:
            result.append({
                "role": msg.role,
                "content": msg.content
            })

        return result

    def get_recent_tool_results(self) -> str:
        """获取最近工具结果的字符串"""
        if not self.tool_results:
            return ""

        parts = []
        for tr in self.tool_results[-self.MAX_TOOL_RESULTS:]:
            parts.append(f"[Tool Result for {tr.tool_name}]\n{tr.get_summary()}\n")

        return "\n".join(parts)

    def _enforce_limits(self) -> None:
        """强制执行容量限制"""
        # 限制消息数量
        while len(self.messages) > self.MAX_MESSAGES:
            # 检查是否要保留工具结果
            if self.messages and self.messages[0].role == "user" and "[Tool Result" in self.messages[0].content:
                # 保留有工具结果的消息
                # 找到第一个不是工具结果的消息
                for i, msg in enumerate(self.messages):
                    if "[Tool Result" not in msg.content:
                        self.messages.pop(i)
                        break
                if not self.messages:
                    break
            else:
                self.messages.pop(0)

        # 限制总字符数
        self._truncate_by_chars()

    def _truncate_by_chars(self) -> None:
        """按总字符数限制截断"""
        total_chars = sum(len(m.content) for m in self.messages)

        if total_chars <= self.MAX_TOTAL_CHARS:
            return

        # 保留最新的消息，截断旧消息
        truncated_messages = []
        current_chars = 0

        for msg in reversed(self.messages):
            if current_chars + len(msg.content) <= self.MAX_TOTAL_CHARS:
                truncated_messages.insert(0, msg)
                current_chars += len(msg.content)
            else:
                # 截断这条消息
                remaining = self.MAX_TOTAL_CHARS - current_chars
                if remaining > 100:  # 至少保留一些内容
                    truncated_content = msg.content[:remaining] + "... [truncated]"
                    truncated_msg = Message(role=msg.role, content=truncated_content)
                    truncated_messages.insert(0, truncated_msg)
                break

        self.messages = truncated_messages

    def should_compact(self) -> bool:
        """检查是否需要压缩"""
        return len(self.messages) >= self.MAX_MESSAGES - 2

    def get_stats(self) -> Dict[str, Any]:
        """获取工作内存统计"""
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "tool_result_count": len(self.tool_results),
            "pending_tool_calls": len(self.pending_tool_calls),
            "total_chars": sum(len(m.content) for m in self.messages),
            "created_at": self._created_at
        }

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
            "tool_results": [tr.to_dict() for tr in self.tool_results],
            "pending_tool_calls": self.pending_tool_calls,
            "created_at": self._created_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkingMemory":
        """从字典恢复"""
        memory = cls(session_id=data.get("session_id", "default"))
        memory.messages = [Message.from_dict(m) for m in data.get("messages", [])]
        memory.tool_results = [ToolResult.from_dict(tr) for tr in data.get("tool_results", [])]
        memory.pending_tool_calls = data.get("pending_tool_calls", [])
        memory._created_at = data.get("created_at", datetime.now().isoformat())
        return memory

    def clear(self) -> None:
        """清空工作内存"""
        self.messages = []
        self.tool_results = []
        self.pending_tool_calls = []


# 工具名称集合（用于判断只读工具）
READONLY_TOOLS = {"read", "list", "glob", "grep", "exists", "get_file_info"}
WRITE_TOOLS = {"write", "edit", "bash"}
ALL_TOOLS = READONLY_TOOLS | WRITE_TOOLS | {"web_search", "web_fetch", "execute_code", "browse"}