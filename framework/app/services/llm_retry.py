"""
LLM Retry Module - 对齐 cc-haha src/services/api/withRetry.ts

核心特性：
1. 专门处理 529 (overloaded) 错误
2. 解析 retry-after header
3. Persistent retry 模式支持长时间等待
4. 模型降级 fallback
5. 前台/后台任务区分重试策略
"""

import asyncio
import time
import random
import logging
from typing import Optional, Dict, Any, AsyncGenerator, Callable
from dataclasses import dataclass, field

from app.core.retry_config import (
    MAX_RETRIES,
    MAX_529_RETRIES,
    BASE_DELAY_MS,
    MAX_DELAY_MS,
    SHORT_RETRY_THRESHOLD_MS,
    MIN_COOLDOWN_MS,
    PERSISTENT_MAX_BACKOFF_MS,
    PERSISTENT_RESET_CAP_MS,
    HEARTBEAT_INTERVAL_MS,
    FOREGROUND_529_RETRY_SOURCES,
)


logger = logging.getLogger(__name__)


# ==================== 异常类 ====================

class CannotRetryError(Exception):
    """不可重试的错误 - 达到最大重试次数或遇到不可恢复错误"""
    def __init__(self, original_error: Exception, retry_context: Dict[str, Any]):
        self.original_error = original_error
        self.retry_context = retry_context
        super().__init__(str(original_error))


class FallbackTriggeredError(Exception):
    """模型降级触发错误"""
    def __init__(self, original_model: str, fallback_model: str):
        self.original_model = original_model
        self.fallback_model = fallback_model
        super().__init__(f"Model fallback triggered: {original_model} -> {fallback_model}")


# ==================== 错误消息结构 ====================

@dataclass
class RetryErrorMessage:
    """重试过程中向用户展示的错误消息"""
    type: str  # "retry", "cooldown", "heartbeat", "error"
    message: str
    delay_ms: Optional[int] = None
    attempt: Optional[int] = None
    max_retries: Optional[int] = None
    error: Optional[str] = None
    remaining_ms: Optional[int] = None


# ==================== RetryService 类 ====================

class LLMRetryService:
    """
    LLM 重试服务 - 对齐 cc-haha 的 withRetry

    使用方式:
        retry_service = LLMRetryService()
        try:
            result = await retry_service.execute_with_retry(
                call_fn=some_llm_call,
                options={"model": "MiniMax-M2.7", ...}
            )
        except CannotRetryError as e:
            # 不可重试的错误
            pass
        except FallbackTriggeredError as e:
            # 模型降级
            pass
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cooldown_until: Optional[float] = None
        self._cooldown_reason: Optional[str] = None
        self._consecutive_529_errors = 0

    # ==================== 错误分类 ====================

    def is_529_error(self, error: Exception) -> bool:
        """
        判断是否是 529 (服务器过载) 错误
        cc-haha: is529Error()
        """
        # 检查 status 属性
        if hasattr(error, 'status') and error.status == 529:
            return True
        # 检查消息内容中是否包含 overloaded
        error_msg = str(error).lower()
        if 'overloaded' in error_msg or '"type":"overloaded_error"' in error_msg:
            return True
        return False

    def is_rate_limit_error(self, error: Exception) -> bool:
        """判断是否是 429 (速率限制) 错误"""
        if hasattr(error, 'status') and error.status == 429:
            return True
        return False

    def is_transient_error(self, error: Exception) -> bool:
        """
        判断是否是临时性错误（应该重试）
        cc-haha: isTransientCapacityError()
        """
        if self.is_529_error(error) or self.is_rate_limit_error(error):
            return True
        if hasattr(error, 'status') and error.status:
            # 5xx 服务器错误
            if 500 <= error.status < 600:
                return True
            # 408 请求超时
            if error.status == 408:
                return True
            # 409 锁超时
            if error.status == 409:
                return True
        return False

    def is_auth_error(self, error: Exception) -> bool:
        """判断是否是认证错误 (401/403)"""
        if hasattr(error, 'status') and error.status in (401, 403):
            return True
        return False

    def is_connection_error(self, error: Exception) -> bool:
        """判断是否是连接错误 (ECONNRESET/EPIPE/Timeout)"""
        error_msg = str(error)
        return (
            'ECONNRESET' in error_msg or
            'EPIPE' in error_msg or
            'Connection reset' in error_msg or
            'Timeout' in error_msg or
            '超时' in error_msg or
            'timed out' in error_msg.lower()
        )

    # ==================== 任务来源判断 ====================

    def should_retry_529(self, query_source: Optional[str]) -> bool:
        """
        判断是否是前台任务，应该重试 529
        cc-haha: shouldRetry529()
        """
        if query_source is None:
            return True  # 默认重试（保守）
        return query_source in FOREGROUND_529_RETRY_SOURCES

    # ==================== Header 解析 ====================

    def get_retry_after_ms(self, error: Exception) -> Optional[int]:
        """
        从错误中提取 retry-after header (单位: ms)
        cc-haha: getRetryAfter()
        """
        if not hasattr(error, 'headers') or not error.headers:
            return None

        headers = error.headers
        if isinstance(headers, dict):
            retry_after = headers.get('retry-after') or headers.get('Retry-After')
        else:
            # 可能是 httpx.Headers 或其他类型
            retry_after = getattr(headers, 'get', lambda x: None)('retry-after')

        if retry_after:
            try:
                seconds = int(retry_after)
                return seconds * 1000
            except ValueError:
                pass
        return None

    def get_rate_limit_reset_delay_ms(self, error: Exception) -> Optional[int]:
        """
        从错误中获取速率限制重置时间（用于 Max/Pro 等套餐）
        cc-haha: getRateLimitResetDelayMs()
        """
        if not hasattr(error, 'headers') or not error.headers:
            return None

        headers = error.headers
        if isinstance(headers, dict):
            reset_header = headers.get('anthropic-ratelimit-unified-reset')
        else:
            reset_header = getattr(headers, 'get', lambda x: None)('anthropic-ratelimit-unified-reset')

        if reset_header:
            try:
                reset_unix_sec = float(reset_header)
                delay_ms = reset_unix_sec * 1000 - time.time() * 1000
                if delay_ms > 0:
                    return min(delay_ms, PERSISTENT_RESET_CAP_MS)
            except ValueError:
                pass
        return None

    # ==================== 延迟计算 ====================

    def get_retry_delay(
        self,
        attempt: int,
        retry_after_ms: Optional[int] = None,
        max_delay_ms: int = MAX_DELAY_MS
    ) -> int:
        """
        计算重试延迟 - 对齐 cc-haha 的 getRetryDelay
        公式: baseDelay * 2^(attempt-1) + jitter

        Args:
            attempt: 当前尝试次数 (从 1 开始)
            retry_after_ms: 服务器返回的 retry-after 延迟 (ms)
            max_delay_ms: 最大延迟上限

        Returns:
            延迟时间 (ms)
        """
        if retry_after_ms is not None:
            return retry_after_ms

        # 指数退避 + 随机抖动
        base_delay = min(BASE_DELAY_MS * (2 ** (attempt - 1)), max_delay_ms)
        jitter = random.random() * 0.25 * base_delay  # 最多 25% 的抖动
        return int(base_delay + jitter)

    def get_persistent_retry_delay(
        self,
        attempt: int,
        retry_after_ms: Optional[int] = None
    ) -> int:
        """
        计算 persistent retry 的延迟（用于 unattend 场景）
        cc-haha: getRetryDelay with persistent config
        """
        if retry_after_ms is not None:
            return min(retry_after_ms, PERSISTENT_RESET_CAP_MS)

        base_delay = min(BASE_DELAY_MS * (2 ** (attempt - 1)), PERSISTENT_MAX_BACKOFF_MS)
        jitter = random.random() * 0.25 * base_delay
        return int(base_delay + jitter)

    # ==================== Cooldown 管理 ====================

    def is_in_cooldown(self) -> bool:
        """检查是否处于 cooldown 状态"""
        if self._cooldown_until is None:
            return False
        return time.time() * 1000 < self._cooldown_until

    def trigger_cooldown(self, duration_ms: int, reason: str) -> None:
        """触发 cooldown"""
        self._cooldown_until = time.time() * 1000 + duration_ms
        self._cooldown_reason = reason
        self.logger.warning(f"LLM cooldown triggered: {reason}, duration={duration_ms}ms")

    def get_cooldown_info(self) -> Optional[Dict[str, Any]]:
        """获取 cooldown 状态信息"""
        if self._cooldown_until is None:
            return None
        if time.time() * 1000 < self._cooldown_until:
            remaining = self._cooldown_until - time.time() * 1000
            return {
                "reason": self._cooldown_reason,
                "remaining_ms": int(remaining),
            }
        return None

    # ==================== 判断是否应该重试 ====================

    def should_retry(
        self,
        error: Exception,
        attempt: int,
        max_retries: int = MAX_RETRIES,
        query_source: Optional[str] = None,
        is_persistent: bool = False,
    ) -> tuple:
        """
        判断是否应该重试

        Returns:
            (should_retry: bool, reason: str, error_type: str)
        """
        # Persistent 模式：只要是临时错误就重试
        if is_persistent and self.is_transient_error(error):
            return True, "persistent_transient", "transient"

        # 连接错误
        if self.is_connection_error(error):
            return True, "connection_error", "connection"

        # 认证错误 - 需要刷新 token
        if self.is_auth_error(error):
            return True, "auth_error_need_refresh", "auth"

        # 529 过载错误
        if self.is_529_error(error):
            # 前台任务重试
            if self.should_retry_529(query_source):
                if attempt <= max_retries * 2:  # 529 多给一次机会
                    return True, "retry_529_foreground", "overloaded"
            return False, "no_retry_529_background", "overloaded"

        # 429 速率限制
        if self.is_rate_limit_error(error):
            if attempt <= max_retries:
                return True, "retry_429", "rate_limit"

        # 5xx 服务器错误
        status = getattr(error, 'status_code', getattr(error, 'status', None))
        if status and 500 <= status < 600:
            if attempt <= max_retries:
                return True, "retry_5xx", "server_error"

        # 408/409 错误
        if status and status in (408, 409):
            if attempt <= max_retries:
                return True, "retry_client_error", "client_error"

        return False, "no_retry_unknown", "unknown"

    # ==================== 重试执行 ====================

    async def execute_with_retry(
        self,
        call_fn: Callable,
        options: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        执行带重试的调用

        Args:
            call_fn: 实际执行 LLM 调用的异步函数
            options: 重试选项

        Options:
            - max_retries: 最大重试次数 (默认 10)
            - model: 当前模型名称
            - fallback_model: 降级模型名称
            - query_source: 任务来源标识
            - is_persistent: 是否是 persistent 模式
            - signal: abort signal
            - on_retry: 重试时的回调函数

        Returns:
            API 响应结果

        Raises:
            CannotRetryError: 不可重试的错误
            FallbackTriggeredError: 模型降级触发
        """
        options = options or {}

        max_retries = options.get('max_retries', MAX_RETRIES)
        model = options.get('model', '')
        fallback_model = options.get('fallback_model')
        query_source = options.get('query_source')
        is_persistent = options.get('is_persistent', False)
        signal = options.get('signal')
        on_retry = options.get('on_retry')

        last_error = None
        self._consecutive_529_errors = 0
        persistent_attempt = 0

        for attempt in range(1, max_retries + 2):  # +1 因为从 1 开始
            # 检查 abort
            if signal and getattr(signal, 'aborted', False):
                raise Exception("Request aborted")

            try:
                result = await call_fn()
                # 成功，重置 529 计数
                self._consecutive_529_errors = 0
                return result

            except Exception as error:
                last_error = error
                error_msg = str(error)

                self.logger.warning(
                    f"[Retry] Attempt {attempt}/{max_retries + 1} failed: "
                    f"{type(error).__name__}: {error_msg[:200]}"
                )

                # === 529 错误处理 ===
                if self.is_529_error(error):
                    self._consecutive_529_errors += 1

                    # 达到 529 最大重试次数，尝试降级
                    if (self._consecutive_529_errors >= MAX_529_RETRIES and
                        fallback_model and
                        self.should_retry_529(query_source)):
                        self.logger.warning(
                            f"529 error after {MAX_529_RETRIES} retries, "
                            f"triggering fallback: {model} -> {fallback_model}"
                        )
                        options['model'] = fallback_model
                        raise FallbackTriggeredError(model, fallback_model)

                    # 外部用户且非 persistent，且不是前台任务
                    if (self._consecutive_529_errors >= MAX_529_RETRIES and
                        not is_persistent and
                        not self.should_retry_529(query_source)):
                        raise CannotRetryError(error, {"model": model, "reason": "529_background"})

                # === 判断是否应该重试 ===
                should_retry, reason, error_type = self.should_retry(
                    error, attempt, max_retries, query_source, is_persistent
                )

                if not should_retry:
                    self.logger.warning(f"[Retry] Not retrying: {reason}")
                    raise CannotRetryError(error, {"model": model, "reason": reason})

                # === 计算延迟 ===
                retry_after_ms = self.get_retry_after_ms(error)

                if is_persistent:
                    delay_ms = self.get_persistent_retry_delay(persistent_attempt, retry_after_ms)
                    persistent_attempt += 1
                else:
                    delay_ms = self.get_retry_delay(attempt, retry_after_ms)

                # === 回调通知 ===
                if on_retry:
                    await on_retry(RetryErrorMessage(
                        type="retry",
                        message=f"Retrying in {delay_ms}ms... (attempt {attempt}/{max_retries})",
                        delay_ms=delay_ms,
                        attempt=attempt,
                        max_retries=max_retries,
                        error=error_msg[:500],
                    ))

                self.logger.info(f"[Retry] Waiting {delay_ms}ms before retry...")

                # === 等待 ===
                await self._sleep_with_heartbeat(delay_ms, signal, on_retry, is_persistent)

        # 达到最大重试次数
        raise CannotRetryError(last_error, {"model": model, "reason": "max_retries_exceeded"})

    async def _sleep_with_heartbeat(
        self,
        delay_ms: int,
        signal,
        on_retry: Optional[Callable] = None,
        is_persistent: bool = False
    ) -> None:
        """带 heartbeat 的等待"""
        if is_persistent and delay_ms > HEARTBEAT_INTERVAL_MS:
            # Persistent 模式下长时间等待，定期发送 heartbeat
            remaining = delay_ms
            while remaining > HEARTBEAT_INTERVAL_MS:
                if signal and getattr(signal, 'aborted', False):
                    raise Exception("Request aborted")

                if on_retry:
                    await on_retry(RetryErrorMessage(
                        type="heartbeat",
                        message=f"Still waiting... {remaining}ms remaining",
                        remaining_ms=remaining,
                    ))

                await asyncio.sleep(HEARTBEAT_INTERVAL_MS / 1000)
                remaining -= HEARTBEAT_INTERVAL_MS

            # 最后一段等待
            if remaining > 0:
                await asyncio.sleep(remaining / 1000)
        else:
            # 普通等待
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

    # ==================== 帮助方法 ====================

    def reset_529_count(self) -> None:
        """重置 529 错误计数"""
        self._consecutive_529_errors = 0


# ==================== 单例 ====================

retry_service = LLMRetryService()