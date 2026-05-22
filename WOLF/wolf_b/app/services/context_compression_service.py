"""
上下文压缩服务 - 用于处理长对话历史的压缩和总结
当对话历史超过阈值时，自动总结早期对话以保持上下文窗口的有效利用
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class Message:
    """消息结构"""
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    timestamp: Optional[float] = None

@dataclass
class ConversationSummary:
    """对话总结"""
    original_count: int  # 原始消息数量
    compressed_count: int  # 压缩后保留的消息数量
    summary: str  # 总结内容
    period_start: Optional[float] = None  # 涵盖的时间范围开始
    period_end: Optional[float] = None  # 涵盖的时间范围结束
    created_at: float = None  # 总结创建时间

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().timestamp()

class ContextCompressionService:
    """
    上下文压缩服务

    功能：
    1. 检测对话历史是否过长
    2. 对早期对话进行总结
    3. 保留最近的关键消息
    4. 在总结和原始消息之间保持连贯性
    """

    # 配置
    MAX_MESSAGES_BEFORE_COMPRESSION = 20  # 超过此数量开始考虑压缩
    MAX_MESSAGES_TO_KEEP = 10  # 压缩后保留的最近消息数量
    SUMMARY_MESSAGE_COUNT = 10  # 每次总结的消息块大小
    MAX_CONTEXT_CHARS = 4000  # 最大上下文字符数（粗略估计）

    def __init__(self, llm_service=None):
        """
        初始化上下文压缩服务

        Args:
            llm_service: LLM 服务实例，用于生成总结（可选）
        """
        self.llm_service = llm_service

    def estimate_token_count(self, text: str) -> int:
        """
        粗略估算 token 数量
        中文约 1.5 tokens/字符，英文约 4 characters/token
        """
        if not text:
            return 0

        # 简单估算：中文 1.5 tokens/字符，英文 4 chars/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars

        return int(chinese_chars * 1.5 + other_chars / 4)

    def should_compress(self, messages: List[Message]) -> bool:
        """
        判断是否需要压缩

        Args:
            messages: 消息列表
        """
        if len(messages) < self.MAX_MESSAGES_BEFORE_COMPRESSION:
            return False

        # 检查总 token 数量是否超过阈值
        total_chars = sum(len(m.content) for m in messages)
        estimated_tokens = self.estimate_token_count("".join(m.content for m in messages))

        # 假设 8000 tokens 是安全阈值
        return estimated_tokens > 8000 or len(messages) > 50

    def compress_messages(
        self,
        messages: List[Message],
        summary: Optional[str] = None
    ) -> Tuple[List[Message], ConversationSummary]:
        """
        压缩对话历史

        Args:
            messages: 原始消息列表
            summary: 可选的预生成总结

        Returns:
            (压缩后的消息列表, 总结对象)
        """
        if len(messages) <= self.MAX_MESSAGES_TO_KEEP:
            return messages, ConversationSummary(
                original_count=len(messages),
                compressed_count=len(messages),
                summary="No compression needed"
            )

        # 分离早期消息和最近消息
        recent_messages = messages[-self.MAX_MESSAGES_TO_KEEP:]
        early_messages = messages[:-self.MAX_MESSAGES_TO_KEEP]

        # 生成总结
        if summary is None:
            summary = self._generate_summary(early_messages)

        # 构建压缩后的消息列表
        compressed = [
            Message(
                role="system",
                content=f"[Earlier conversation summary - {len(early_messages)} messages]:\n\n{summary}"
            )
        ]
        compressed.extend(recent_messages)

        period_start = early_messages[0].timestamp if early_messages and early_messages[0].timestamp else None
        period_end = early_messages[-1].timestamp if early_messages and early_messages[-1].timestamp else None

        conversation_summary = ConversationSummary(
            original_count=len(messages),
            compressed_count=len(compressed),
            summary=summary,
            period_start=period_start,
            period_end=period_end
        )

        return compressed, conversation_summary

    def _generate_summary(self, messages: List[Message]) -> str:
        """
        生成对话总结

        Args:
            messages: 要总结的消息列表
        """
        if not messages:
            return "No earlier messages."

        # 如果没有 LLM 服务，使用简单的提取方法
        if self.llm_service is None:
            return self._simple_summary(messages)

        try:
            # 构建总结提示
            conversation_text = "\n".join([
                f"{'User' if m.role == 'user' else 'Assistant'}: {m.content[:500]}"
                + ("..." if len(m.content) > 500 else "")
                for m in messages
            ])

            summary_prompt = f"""请总结以下对话的要点，保留关键信息和结论：

{conversation_text[:3000]}

请用简洁的语言总结：
1. 对话的主要话题
2. 关键结论或决定
3. 用户的主要需求或问题

总结："""

            # 调用 LLM 生成总结
            import asyncio
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self.llm_service.complete(
                    prompt=summary_prompt,
                    system_prompt="你是一个对话总结助手，擅长提取对话的核心要点。"
                )
            )
            loop.close()

            if result.get("success"):
                return result.get("content", "")[:1000]  # 限制总结长度
            else:
                return self._simple_summary(messages)

        except Exception:
            return self._simple_summary(messages)

    def _simple_summary(self, messages: List[Message]) -> str:
        """
        简单总结方法（不依赖 LLM）

        Args:
            messages: 消息列表
        """
        if not messages:
            return "No earlier messages."

        # 提取关键信息
        topics = []
        user_intents = []

        for m in messages:
            if m.role == "user":
                # 提取前几个字的意图
                content_preview = m.content[:100].replace('\n', ' ')
                user_intents.append(content_preview)

        # 简单总结
        summary_parts = [f"共 {len(messages)} 条消息"]

        if user_intents:
            # 取最后一条用户消息作为当前话题的指示
            last_topic = user_intents[-1][:50] if user_intents else ""
            if last_topic:
                summary_parts.append(f"最后话题: {last_topic}")

        # 统计对话轮次
        user_count = sum(1 for m in messages if m.role == "user")
        assistant_count = sum(1 for m in messages if m.role == "assistant")

        summary_parts.append(f"用户消息: {user_count}条, 助手消息: {assistant_count}条")

        return "; ".join(summary_parts)

    def split_large_context(
        self,
        messages: List[Message],
        max_tokens_per_chunk: int = 6000
    ) -> List[List[Message]]:
        """
        将大型对话历史分割成多个块

        Args:
            messages: 消息列表
            max_tokens_per_chunk: 每块的最大 token 数
        """
        if not messages:
            return []

        chunks = []
        current_chunk = []
        current_tokens = 0

        for message in messages:
            message_tokens = self.estimate_token_count(message.content) + 10  # 加权值

            if current_tokens + message_tokens > max_tokens_per_chunk and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [message]
                current_tokens = message_tokens
            else:
                current_chunk.append(message)
                current_tokens += message_tokens

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def compress_with_llm(
        self,
        messages: List[Message],
        system_prompt: str = ""
    ) -> Tuple[List[Message], ConversationSummary]:
        """
        使用 LLM 进行智能压缩

        Args:
            messages: 消息列表
            system_prompt: 系统提示
        """
        if self.llm_service is None:
            return self.compress_messages(messages)

        # 检查是否需要压缩
        if not self.should_compress(messages):
            return messages, ConversationSummary(
                original_count=len(messages),
                compressed_count=len(messages),
                summary="No compression needed"
            )

        try:
            # 构建压缩提示
            conversation_text = self._format_messages_for_summary(messages)

            compression_prompt = f"""请分析以下对话历史，生成一个简洁的总结：

{conversation_text}

请按以下格式总结：
## 对话主题
[一句话描述主要话题]

## 关键信息
- [关键点1]
- [关键点2]
- [关键点3]

## 结论/结果
[如有明确结论]

## 遗留问题
[如有未解决的问题]"""

            result = await self.llm_service.complete(
                prompt=compression_prompt,
                system_prompt=system_prompt or "你是一个专业的对话总结助手，擅长提取关键信息。"
            )

            if result.get("success"):
                summary = result.get("content", "")
                return self.compress_messages(messages, summary=summary)
            else:
                return self.compress_messages(messages)

        except Exception:
            return self.compress_messages(messages)

    def _format_messages_for_summary(self, messages: List[Message], max_chars: int = 4000) -> str:
        """格式化消息用于总结"""
        lines = []
        total_chars = 0

        for m in messages:
            prefix = "用户" if m.role == "user" else "助手"
            content = m.content[:500] + ("..." if len(m.content) > 500 else "")
            line = f"{prefix}: {content}"

            if total_chars + len(line) > max_chars:
                break

            lines.append(line)
            total_chars += len(line)

        return "\n".join(lines)


# 全局实例
compression_service = ContextCompressionService()


# 便捷函数
def should_compress(messages: List[Message]) -> bool:
    """判断是否需要压缩"""
    return compression_service.should_compress(messages)

def compress_messages(
    messages: List[Message],
    summary: Optional[str] = None
) -> Tuple[List[Message], ConversationSummary]:
    """压缩消息"""
    return compression_service.compress_messages(messages, summary)

def split_large_context(
    messages: List[Message],
    max_tokens_per_chunk: int = 6000
) -> List[List[Message]]:
    """分割大型上下文"""
    return compression_service.split_large_context(messages, max_tokens_per_chunk)
