"""
Message normalization service - 参照 cc 的 normalizeMessagesForAPI
"""
from typing import List, Set, Optional
from app.types.message import (
    Message,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    is_virtual_message,
    is_local_command_system,
    parse_history_item,
)


def normalize_messages_for_api(
    messages: List[Message],
    tools: List[dict] = None
) -> List[Message]:
    """
    规范化消息用于 API 调用 - 参照 cc 的 normalizeMessagesForAPI

    主要功能：
    1. 重新排序附件（attachment）
    2. 过滤虚拟消息（isVirtual）
    3. 过滤 system 消息（保留 local_command）
    4. 过滤 synthetic API error messages
    5. 去除空内容的消息
    """
    if tools is None:
        tools = []

    # 构建可用工具名称集合
    available_tool_names = set(t.get("name") for t in tools if isinstance(t, dict))

    # Step 1: 重新排序附件，过滤虚拟消息
    reordered = _reorder_attachments_for_api(messages)
    filtered = [m for m in reordered if not is_virtual_message(m)]

    # Step 2: 构建 strip targets map（用于过滤错误消息）
    strip_targets = _build_strip_targets(filtered)

    # Step 3: 过滤并转换消息
    result = []
    for msg in filtered:
        if _should_filter_message(msg):
            continue

        # 应用 strip targets
        if isinstance(msg, UserMessage) and hasattr(msg, 'uuid'):
            uuid = msg.uuid
            if uuid in strip_targets:
                # 剥离指定类型的 blocks
                msg.content = _strip_blocks_by_type(
                    msg.content,
                    strip_targets[uuid]
                )

        if isinstance(msg, SystemMessage):
            # local_command system messages 转为 user messages
            if is_local_command_system(msg):
                result.append(_convert_local_command_to_user(msg))
        else:
            result.append(msg)

    return result


def _is_virtual_message(msg: Message) -> bool:
    """检查是否是虚拟消息"""
    return is_virtual_message(msg)


def _should_filter_message(msg: Message) -> bool:
    """检查消息是否应该被过滤"""
    # 过滤 progress 消息
    if hasattr(msg, 'type') and msg.type == "progress":
        return True

    # 过滤 system 消息（非 local_command）
    if isinstance(msg, SystemMessage):
        return not is_local_command_system(msg)

    # 过滤 synthetic API error messages
    if _is_synthetic_api_error_message(msg):
        return True

    # 过滤空内容
    if hasattr(msg, 'content'):
        if isinstance(msg.content, list) and len(msg.content) == 0:
            return True
        if isinstance(msg.content, str) and not msg.content.strip():
            return True

    return False


def _is_synthetic_api_error_message(msg: Message) -> bool:
    """检查是否是 synthetic API error message"""
    if isinstance(msg, UserMessage):
        content = msg.content
        if isinstance(content, list) and len(content) > 0:
            first = content[0]
            if isinstance(first, ToolResultBlock):
                return "[Error]" in first.content or "Error" in first.content
    return False


def _reorder_attachments_for_api(messages: List[Message]) -> List[Message]:
    """重新排序附件 - 把附件移动到工具结果或 assistant 消息之前"""
    result = []
    pending_attachments = []

    for msg in messages:
        # 检查是否是带有附件的用户消息
        if isinstance(msg, UserMessage):
            content = msg.content
            if isinstance(content, list):
                # 检查是否有附件类型的 block
                has_attachment = any(
                    hasattr(c, 'type') and c.type == 'attachment'
                    for c in content
                )
                if has_attachment:
                    # 延迟附件直到遇到 tool result 或 assistant
                    pending_attachments.append(msg)
                    continue

        # 非附件消息
        if pending_attachments:
            result.extend(pending_attachments)
            pending_attachments = []
        result.append(msg)

    # 处理剩余的附件
    if pending_attachments:
        result.extend(pending_attachments)

    return result


def _build_strip_targets(messages: List[Message]) -> dict:
    """构建需要剥离的 block 类型映射"""
    targets = {}

    for i, msg in enumerate(messages):
        if _is_synthetic_api_error_message(msg):
            # 获取错误文本
            error_text = _get_error_text_from_message(msg)
            if not error_text:
                continue

            # 向后查找最近的 is_meta user message
            for j in range(i - 1, -1, -1):
                candidate = messages[j]
                if isinstance(candidate, UserMessage) and hasattr(candidate, 'is_meta') and candidate.is_meta:
                    targets[candidate.uuid] = _get_block_types_to_strip(error_text)
                    break
                if isinstance(candidate, AssistantMessage):
                    break
                if _is_synthetic_api_error_message(candidate):
                    continue

    return targets


def _get_error_text_from_message(msg: Message) -> Optional[str]:
    """从错误消息中获取错误文本"""
    if isinstance(msg, UserMessage):
        content = msg.content
        if isinstance(content, list) and len(content) > 0:
            first = content[0]
            if isinstance(first, ToolResultBlock):
                return first.content
    return None


def _get_block_types_to_strip(error_text: str) -> set:
    """根据错误文本确定要剥离的 block 类型"""
    strip_map = {
        "PDF too large": {"document"},
        "PDF password protected": {"document"},
        "Image too large": {"image"},
        "Request too large": {"document", "image"},
    }

    types_to_strip = set()
    for key, types in strip_map.items():
        if key in error_text:
            types_to_strip.update(types)

    return types_to_strip


def _strip_blocks_by_type(content: list, block_types: set) -> list:
    """从 content 中剥离指定类型的 blocks"""
    if not block_types:
        return content

    result = []
    for block in content:
        if hasattr(block, 'type') and block.type in block_types:
            continue
        result.append(block)

    return result


def _convert_local_command_to_user(msg: SystemMessage) -> UserMessage:
    """将 local_command system message 转换为 user message"""
    import uuid
    from datetime import datetime

    return UserMessage(
        type="user",
        uuid=str(uuid.uuid4()),
        timestamp=int(datetime.now().timestamp() * 1000),
        content=[TextBlock(text=msg.content)],
        is_meta=False,
        is_virtual=False
    )


def convert_history_list_to_messages(history_list: List[dict]) -> List[Message]:
    """
    将前端传来的 history_list 转换为内部 Message 对象

    支持多种格式：
    1. {"role": "user", "content": "..."}
    2. {"agentRole": "user", "content": "..."}
    3. {"sessionId": ..., "agentRole": ..., "content": ..., "id": ..., "timestamp": ...}
    """
    if not history_list:
        return []

    messages = []
    for item in history_list:
        msg = parse_history_item(item)
        if msg:
            messages.append(msg)

    return messages


def format_messages_for_llm(messages: List[Message]) -> List[dict]:
    """
    将 Message 对象列表格式化为 LLM 可用的消息列表
    """
    result = []

    for msg in messages:
        if isinstance(msg, UserMessage):
            content = _format_content_blocks(msg.content)
            result.append({"role": "user", "content": content})
        elif isinstance(msg, AssistantMessage):
            content = _format_content_blocks(msg.content)
            result.append({"role": "assistant", "content": content})
        elif isinstance(msg, SystemMessage):
            result.append({"role": "system", "content": msg.content})

    return result


def _format_content_blocks(content) -> str:
    """格式化 content blocks 为字符串"""
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return str(content)

    parts = []
    for block in content:
        if hasattr(block, 'text'):
            parts.append(block.text)
        elif hasattr(block, 'type') and block.type == 'tool_use':
            parts.append(f"<{getattr(block, 'name', 'unknown')}>")
        elif hasattr(block, 'type') and block.type == 'tool_result':
            parts.append(f"[Tool Result]: {getattr(block, 'content', '')}")
        elif hasattr(block, 'thinking'):
            parts.append(f"[Thinking]: {block.thinking}")

    return "\n".join(parts) if parts else ""