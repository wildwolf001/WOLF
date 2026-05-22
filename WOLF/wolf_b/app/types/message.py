"""
Message type system - 参照 cc-haha 的 Message 类型
"""
from dataclasses import dataclass, field
from typing import List, Union, Optional, Literal, Any
from enum import Enum
import uuid
from datetime import datetime


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    PROGRESS = "progress"
    TOMBSTONE = "tombstone"


@dataclass
class TextBlock:
    """文本块"""
    text: str
    type: Literal["text"] = "text"


@dataclass
class ToolUseBlock:
    """工具调用块"""
    id: str
    name: str
    input: dict
    type: Literal["tool_use"] = "tool_use"


@dataclass
class ToolResultBlock:
    """工具结果块"""
    content: str
    id: str  # tool_use_id
    is_error: bool = False
    type: Literal["tool_result"] = "tool_result"


@dataclass
class ThinkingBlock:
    """思考块"""
    thinking: str
    type: Literal["thinking"] = "thinking"


@dataclass
class AttachmentBlock:
    """附件块"""
    name: str
    attachment_type: str  # "file", "image", etc.
    type: Literal["attachment"] = "attachment"
    path: Optional[str] = None
    content: Optional[str] = None


# Content blocks - union type
ContentBlock = Union[TextBlock, ToolUseBlock, ToolResultBlock, ThinkingBlock, AttachmentBlock]


@dataclass
class UserMessage:
    """用户消息 - 对应 cc 的 UserMessage"""
    uuid: str
    timestamp: int
    content: List[ContentBlock]
    type: Literal["user"] = "user"
    is_meta: bool = False
    is_virtual: bool = False

    @staticmethod
    def create(content: str, role: str = "user", msg_id: str = None, timestamp: int = None) -> 'UserMessage':
        """创建 UserMessage 的便捷方法"""
        return UserMessage(
            uuid=msg_id or str(uuid.uuid4()),
            timestamp=timestamp or int(datetime.now().timestamp() * 1000),
            content=[TextBlock(text=content)] if isinstance(content, str) else content,
            type="user" if role == "user" else "assistant",
            is_meta=False,
            is_virtual=False
        )


@dataclass
class AssistantMessage:
    """Assistant message - 对应 cc 的 AssistantMessage"""
    uuid: str
    timestamp: int
    content: List[ContentBlock]
    type: Literal["assistant"] = "assistant"
    stop_reason: Optional[str] = None
    is_virtual: bool = False

    @staticmethod
    def create(content: str, msg_id: str = None, timestamp: int = None) -> 'AssistantMessage':
        """创建 AssistantMessage 的便捷方法"""
        return AssistantMessage(
            uuid=msg_id or str(uuid.uuid4()),
            timestamp=timestamp or int(datetime.now().timestamp() * 1000),
            content=[TextBlock(text=content)] if isinstance(content, str) else content,
            type="assistant",
            stop_reason=None,
            is_virtual=False
        )


@dataclass
class SystemMessage:
    """System message"""
    uuid: str
    timestamp: int
    content: str
    type: Literal["system"] = "system"
    is_local_command: bool = False


@dataclass
class ProgressMessage:
    """Progress message for real-time updates"""
    progress: dict
    type: Literal["progress"] = "progress"


@dataclass
class TombstoneMessage:
    """Tombstone message - deleted message placeholder"""
    uuid: str
    original_type: str
    type: Literal["tombstone"] = "tombstone"


# Union type for all messages
Message = Union[UserMessage, AssistantMessage, SystemMessage, ProgressMessage, TombstoneMessage]


def is_virtual_message(msg: Message) -> bool:
    """检查是否是虚拟消息"""
    if isinstance(msg, (UserMessage, AssistantMessage)):
        return msg.is_virtual
    return False


def is_local_command_system(msg: Message) -> bool:
    """检查是否是 local_command system message"""
    if isinstance(msg, SystemMessage):
        return msg.is_local_command or msg.content.startswith("[Local Command]")
    return False


def get_message_type(msg: Message) -> str:
    """获取消息类型字符串"""
    return msg.type if hasattr(msg, 'type') else 'unknown'


def format_message_for_api(msg: Message) -> dict:
    """将消息格式化为 API 格式"""
    if isinstance(msg, UserMessage):
        return {
            "role": "user",
            "content": _format_content(msg.content)
        }
    elif isinstance(msg, AssistantMessage):
        return {
            "role": "assistant",
            "content": _format_content(msg.content)
        }
    elif isinstance(msg, SystemMessage):
        return {
            "role": "system",
            "content": msg.content
        }
    return {"role": "unknown", "content": ""}


def _format_content(content: List[ContentBlock]) -> str:
    """格式化 content blocks 为字符串"""
    if isinstance(content, str):
        return content

    parts = []
    for block in content:
        if isinstance(block, TextBlock):
            parts.append(block.text)
        elif isinstance(block, ToolUseBlock):
            parts.append(f"<{block.name}>")
        elif isinstance(block, ToolResultBlock):
            parts.append(f"[Tool Result]: {block.content}")
        elif isinstance(block, ThinkingBlock):
            parts.append(f"[Thinking]: {block.thinking}")
    return "\n".join(parts) if parts else ""


def parse_history_item(item: dict) -> Optional[Message]:
    """
    解析历史记录项为 Message 对象
    支持多种格式：
    1. {"role": "user", "content": "..."}
    2. {"agentRole": "user", "content": "..."}
    3. {"sessionId": ..., "agentRole": ..., "content": ..., "id": ..., "timestamp": ...}
    """
    if not isinstance(item, dict):
        return None

    # 获取 role（支持多种键名）
    role = item.get("role") or item.get("agentRole") or item.get("type")
    if not role:
        return None

    # 获取 content
    content = item.get("content", "")
    if not content:
        return None

    # 获取 optional 字段
    msg_id = item.get("id") or item.get("uuid") or str(uuid.uuid4())
    timestamp = item.get("timestamp") or int(datetime.now().timestamp() * 1000)
    is_meta = item.get("isMeta", False)
    is_virtual = item.get("isVirtual", False)

    # 创建消息
    if role in ["user", "assistant"]:
        text_block = TextBlock(text=content) if isinstance(content, str) else content
        content_blocks = [text_block] if isinstance(content, str) else content

        if role == "user":
            return UserMessage(
                type="user",
                uuid=msg_id,
                timestamp=timestamp,
                content=content_blocks,
                is_meta=is_meta,
                is_virtual=is_virtual
            )
        else:
            return AssistantMessage(
                type="assistant",
                uuid=msg_id,
                timestamp=timestamp,
                content=content_blocks,
                stop_reason=item.get("stop_reason")
            )
    elif role == "system":
        return SystemMessage(
            type="system",
            uuid=msg_id,
            timestamp=timestamp,
            content=content,
            is_local_command=item.get("isLocalCommand", False)
        )

    return None