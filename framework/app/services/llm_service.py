"""
LLM Service - Unified interface for multiple LLM providers with error handling and circuit breaker
Supports: MiniMax, DeepSeek, Qwen, OpenAI, Anthropic, Zhipu, Moonshot
"""
import httpx
import asyncio
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from app.core.runtime_config import runtime_config, LLM_PROVIDERS, MINIMAX_BASE_URL
from app.core.retry_config import MAX_RETRIES, BASE_DELAY_MS
from app.observability.tracker import get_stats_aggregator
from app.observability.cost import get_cost_calculator
from app.services.llm_retry import (
    retry_service,
    CannotRetryError,
    FallbackTriggeredError,
)


class LLMErrorType(Enum):
    """LLM error types"""
    API_ERROR = "API_ERROR"           # Network, timeout, 5xx
    AUTH_ERROR = "AUTH_ERROR"         # 401, 403
    RATE_LIMIT = "RATE_LIMIT"        # 429
    MODEL_ERROR = "MODEL_ERROR"       # 406, model not supported
    MAX_OUTPUT_TOKENS = "MAX_OUTPUT_TOKENS"  # Output limit reached
    UNKNOWN = "UNKNOWN"


class LLMError(Exception):
    """Custom LLM error with structured information"""
    def __init__(
        self,
        error_type: LLMErrorType,
        provider: str,
        message: str,
        recoverable: bool = True,
        status_code: Optional[int] = None,
        headers: Optional[Dict] = None
    ):
        self.error_type = error_type
        self.provider = provider
        self.message = message
        self.recoverable = recoverable
        self.status_code = status_code
        self.headers = headers or {}  # 添加 headers 属性，支持 retry-after 解析
        super().__init__(message)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class ProviderCircuit:
    """Circuit breaker for a single provider"""
    def __init__(self, provider: str, failure_threshold: int = 3, reset_timeout: int = 300):
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout  # seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.test_attempts = 0

    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            return True  # Circuit opened
        return False

    def record_success(self):
        """Record a success and close the circuit"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.test_attempts = 0

    def can_attempt(self) -> bool:
        """Check if a request can be made"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.reset_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.test_attempts += 1
                    return True
            return False

        # HALF_OPEN - allow one test request
        if self.test_attempts < 1:
            self.test_attempts += 1
            return True
        return False

    def get_status(self) -> str:
        """Get current circuit status"""
        if self.state == CircuitState.CLOSED:
            return "healthy" if self.failure_count == 0 else f"degraded({self.failure_count})"
        elif self.state == CircuitState.OPEN:
            return "unavailable"
        else:
            return "testing"


class LLMService:
    """Unified LLM service with error handling and circuit breaker"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or runtime_config.current_provider
        self.circuits: Dict[str, ProviderCircuit] = {}
        self.logger = logging.getLogger(__name__)
        self._init_circuits()

    def _init_circuits(self):
        """Initialize circuit breakers for all providers"""
        for provider_id in LLM_PROVIDERS.keys():
            self.circuits[provider_id] = ProviderCircuit(provider_id)

    def _get_circuit(self, provider: str) -> ProviderCircuit:
        """Get or create circuit for provider"""
        if provider not in self.circuits:
            self.circuits[provider] = ProviderCircuit(provider)
        return self.circuits[provider]

    def _classify_error(self, e: Exception, provider: str, status_code: Optional[int] = None, headers: Optional[Dict] = None) -> LLMError:
        """Classify error type from exception"""
        if isinstance(e, httpx.HTTPError):
            if status_code:
                if status_code == 401 or status_code == 403:
                    return LLMError(
                        LLMErrorType.AUTH_ERROR, provider,
                        f"认证失败: {str(e)}", recoverable=False, status_code=status_code,
                        headers=headers
                    )
                elif status_code == 429:
                    return LLMError(
                        LLMErrorType.RATE_LIMIT, provider,
                        f"请求限流: {str(e)}", recoverable=True, status_code=status_code,
                        headers=headers
                    )
                elif status_code == 406:
                    return LLMError(
                        LLMErrorType.MODEL_ERROR, provider,
                        f"模型不支持: {str(e)}", recoverable=True, status_code=status_code,
                        headers=headers
                    )
                elif 500 <= status_code < 600:
                    return LLMError(
                        LLMErrorType.API_ERROR, provider,
                        f"服务器错误: {str(e)}", recoverable=True, status_code=status_code,
                        headers=headers
                    )

            # Timeout or connection error
            if isinstance(e, httpx.TimeoutException):
                return LLMError(
                    LLMErrorType.API_ERROR, provider,
                    f"请求超时: {str(e)}", recoverable=True, status_code=status_code,
                    headers=headers
                )
            return LLMError(
                LLMErrorType.API_ERROR, provider,
                f"API错误: {str(e)}", recoverable=True, status_code=status_code,
                headers=headers
            )

        return LLMError(
            LLMErrorType.UNKNOWN, provider,
            f"未知错误: {str(e)}", recoverable=False, status_code=status_code,
            headers=headers
        )

    def _get_all_providers(self) -> list:
        """Get all available providers in priority order"""
        providers = list(LLM_PROVIDERS.keys())
        # Move current provider to front
        if self.provider in providers:
            providers.remove(self.provider)
            providers.insert(0, self.provider)
        return providers

    async def complete(
        self,
        prompt: str = None,
        system_prompt: Optional[str] = None,
        max_retries: int = MAX_RETRIES,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        fallback_model: Optional[str] = None,
        query_source: Optional[str] = None,
        is_persistent: bool = False,
        signal=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a completion request with error handling and fallback.
        对齐 cc-haha: 支持重试、模型降级、retry-after 解析

        Args:
            prompt: The user's prompt (used if messages is not provided)
            system_prompt: Optional system prompt
            max_retries: Maximum retries per provider (default 10)
            messages: Optional list of message dicts for multi-turn conversation
            tools: Optional list of tool definitions for function calling
            max_tokens: Maximum output tokens (default 4096)
            fallback_model: 模型降级备选
            query_source: 任务来源标识，用于判断是否重试 529
            is_persistent: 是否是 persistent 模式 (长时间等待)
            signal: abort signal

        Returns:
            Dict with 'success', 'content', 'tool_calls', and optionally 'error' keys
        """
        tools = kwargs.pop('tools', tools)  # Support tools in kwargs too

        # Try each provider in order
        providers_to_try = self._get_all_providers()

        for provider in providers_to_try:
            circuit = self._get_circuit(provider)

            if not circuit.can_attempt():
                continue

            config = runtime_config.providers.get(provider)
            if not config or not config.api_key:
                continue

            # 设置当前 provider 的模型
            current_model = config.model

            try:
                result = await self._call_with_retry(
                    provider=provider,
                    config=config,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens,
                    max_retries=max_retries,
                    fallback_model=fallback_model,
                    query_source=query_source,
                    is_persistent=is_persistent,
                    signal=signal,
                    **kwargs
                )
                circuit.record_success()
                return result

            except FallbackTriggeredError as e:
                # 模型降级，尝试备用模型
                self.logger.warning(f"Fallback triggered: {e.original_model} -> {e.fallback_model}")
                # 切换到 fallback provider 或使用备用模型
                if fallback_model and provider == self.provider:
                    config.model = fallback_model
                    try:
                        result = await self._call_with_retry(
                            provider=provider,
                            config=config,
                            prompt=prompt,
                            system_prompt=system_prompt,
                            messages=messages,
                            tools=tools,
                            max_tokens=max_tokens,
                            max_retries=max_retries,
                            fallback_model=None,  # 避免循环
                            query_source=query_source,
                            is_persistent=is_persistent,
                            signal=signal,
                            **kwargs
                        )
                        return result
                    except Exception:
                        pass
                circuit.record_failure()
                continue

            except CannotRetryError as e:
                self.logger.warning(f"Cannot retry error: {e}")
                circuit.record_failure()
                continue

            except LLMError as e:
                self.logger.warning(f"LLM Error: {e}")
                circuit.record_failure()

                # Non-recoverable errors - don't retry this provider
                if not e.recoverable:
                    continue

                # 继续下一个 provider
                continue

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                circuit.record_failure()
                continue

        # All providers failed
        return {
            "success": False,
            "error": "All providers failed",
            "content": None,
            "provider": None
        }

    async def _call_with_retry(
        self,
        provider: str,
        config,
        prompt: str,
        system_prompt: Optional[str],
        messages: Optional[List[Dict[str, Any]]],
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: int,
        max_retries: int = MAX_RETRIES,
        fallback_model: Optional[str] = None,
        query_source: Optional[str] = None,
        is_persistent: bool = False,
        signal=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        带重试的 provider 调用 - 对齐 cc-haha withRetry
        """
        retry_options = {
            'max_retries': max_retries,
            'model': config.model,
            'fallback_model': fallback_model,
            'query_source': query_source,
            'is_persistent': is_persistent,
            'signal': signal,
        }

        async def call_fn():
            return await self._call_provider(
                provider, config, prompt, system_prompt, messages, tools, max_tokens=max_tokens, **kwargs
            )

        result = await retry_service.execute_with_retry(call_fn, retry_options)
        return result

    async def stream_complete(
        self,
        prompt: str = None,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        event_callback=None,
        max_tokens: int = 4096,
        **kwargs
    ):
        """
        Streaming completion with structured events.

        对齐 cc-haha 的流式响应模式，yield 多种事件类型：
        - content_delta: 文本内容片段
        - tool_use: 工具调用块
        - tool_use_block_start: 工具调用开始
        - tool_use_block_end: 工具调用结束
        - message_end: 消息结束

        Args:
            prompt: The user's prompt (used if messages is not provided)
            system_prompt: Optional system prompt
            messages: Optional list of message dicts for multi-turn conversation
            tools: Optional list of tool definitions for function calling
            event_callback: Async callback function called with event dict
            max_tokens: Maximum output tokens
            **kwargs: Additional provider-specific arguments

        Yields:
            Event dicts with 'type' and relevant data
        """
        # Use provided messages if available, otherwise build from prompt/system
        if messages:
            final_messages = messages
            # Always prepend system prompt if provided (don't ignore it!)
            if system_prompt and not any(m.get("role") == "system" for m in messages):
                final_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            final_messages = []
            if system_prompt:
                final_messages.append({"role": "system", "content": system_prompt})
            if prompt:
                final_messages.append({"role": "user", "content": prompt})

        # Try each provider in order
        providers_to_try = self._get_all_providers()

        for provider in providers_to_try:
            circuit = self._get_circuit(provider)

            if not circuit.can_attempt():
                continue

            config = runtime_config.providers.get(provider)
            if not config or not config.api_key:
                continue

            try:
                # Call provider's streaming method with event support
                async for event in self._call_provider_stream_events(
                    provider, config, final_messages, tools, event_callback, max_tokens, **kwargs
                ):
                    yield event
                circuit.record_success()
                return
            except LLMError as e:
                circuit.record_failure()
                continue
            except Exception as e:
                circuit = self._get_circuit(provider)
                circuit.record_failure()
                continue

        raise LLMError(LLMErrorType.API_ERROR, "all", "All providers failed", recoverable=False)

    async def _call_provider_stream_events(
        self,
        provider: str,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        event_callback=None,
        max_tokens: int = 4096,
        **kwargs
    ):
        """
        Call provider in streaming mode, yielding structured events.

        Returns structured events:
        - {"type": "content_delta", "content": "..."}
        - {"type": "tool_use", "id": "...", "name": "...", "arguments": {...}}
        - {"type": "message_end", "stop_reason": "..."}
        """
        if provider == "minimax":
            async for event in self._minimax_stream_events(config, messages, tools, event_callback, max_tokens, **kwargs):
                yield event
        elif provider == "deepseek":
            async for event in self._deepseek_stream_events(config, messages, tools, event_callback, **kwargs):
                yield event
        elif provider == "openai":
            async for event in self._openai_stream_events(config, messages, tools, event_callback, **kwargs):
                yield event
        elif provider == "anthropic":
            async for event in self._anthropic_stream_events(config, messages, tools, event_callback, max_tokens, **kwargs):
                yield event
        else:
            # Fallback: use non-streaming and simulate
            result = await self._call_provider(provider, config, None, None, messages, tools, max_tokens=max_tokens, **kwargs)
            if result.get("success"):
                content = result.get("content", "")
                for char in content:
                    yield {"type": "content_delta", "content": char}
                for tc in result.get("tool_calls", []):
                    yield {"type": "tool_use", **tc}
            yield {"type": "message_end", "stop_reason": "end_turn"}

    async def _call_provider(
        self,
        provider: str,
        config,
        prompt: str,
        system_prompt: Optional[str],
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call a specific provider - raises LLMError on failure"""
        model = getattr(config, 'model', provider)
        start = time.time()

        try:
            if provider == "minimax":
                result = await self._minimax_complete(prompt, system_prompt, config, messages, tools, **kwargs)
            elif provider == "deepseek":
                result = await self._deepseek_complete(prompt, system_prompt, config, messages, tools, **kwargs)
            elif provider == "qwen":
                result = await self._qwen_complete(prompt, system_prompt, config, messages, tools, **kwargs)
            elif provider == "openai":
                result = await self._openai_complete(prompt, system_prompt, config, messages, tools, **kwargs)
            elif provider == "anthropic":
                result = await self._anthropic_complete(prompt, system_prompt, config, messages, tools, **kwargs)
            elif provider == "zhipu":
                result = await self._zhipu_complete(prompt, system_prompt, config, messages, tools, **kwargs)
            elif provider == "moonshot":
                result = await self._moonshot_complete(prompt, system_prompt, config, messages, tools, **kwargs)
            else:
                raise LLMError(LLMErrorType.UNKNOWN, provider, f"Unknown provider: {provider}", recoverable=False)

            # Track successful call
            elapsed_ms = (time.time() - start) * 1000
            input_text = (prompt or "") + (system_prompt or "") + str(messages or "")
            output_text = str(result.get("content", "") or "")
            input_tokens = max(len(input_text) // 3, 1)
            output_tokens = max(len(output_text) // 3, 1)
            get_stats_aggregator().record(
                model=model, input_tokens=input_tokens, output_tokens=output_tokens,
                latency_ms=elapsed_ms, success=True
            )
            get_cost_calculator().record(model=model, input_tokens=input_tokens, output_tokens=output_tokens)
            return result

        except Exception:
            elapsed_ms = (time.time() - start) * 1000
            get_stats_aggregator().record(
                model=model, input_tokens=0, output_tokens=0,
                latency_ms=elapsed_ms, success=False
            )
            raise

    async def _call_provider_stream(
        self,
        provider: str,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        content_callback=None,
        **kwargs
    ):
        """Call a specific provider in streaming mode - yields content chunks"""
        if provider == "minimax":
            async for chunk in self._minimax_complete_stream(config, messages, tools, content_callback, **kwargs):
                yield chunk
        elif provider == "deepseek":
            async for chunk in self._deepseek_complete_stream(config, messages, tools, content_callback, **kwargs):
                yield chunk
        elif provider == "openai":
            async for chunk in self._openai_complete_stream(config, messages, tools, content_callback, **kwargs):
                yield chunk
        elif provider == "anthropic":
            async for chunk in self._anthropic_complete_stream(config, messages, tools, content_callback, **kwargs):
                yield chunk
        else:
            # Fallback: use non-streaming and simulate chunks
            result = await self._call_provider(provider, config, None, None, messages, tools, **kwargs)
            if result.get("success"):
                content = result.get("content", "")
                if content_callback:
                    # Simulate streaming by yielding in chunks
                    chunk_size = 50
                    for i in range(0, len(content), chunk_size):
                        await content_callback(content[i:i+chunk_size])
                        yield content[i:i+chunk_size]
            else:
                yield content

    async def _minimax_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        config,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call MiniMax API with optional function calling support"""
        api_key = config.api_key
        group_id = config.group_id
        model = config.model or "MiniMax-M2.7"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "minimax", "API key not configured", recoverable=False)

        # Use provided messages if available, otherwise build from prompt/system
        if messages:
            final_messages = messages
            # Always prepend system prompt if provided (don't ignore it!)
            if system_prompt and not any(m.get("role") == "system" for m in messages):
                final_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            final_messages = []
            if system_prompt:
                final_messages.append({"role": "system", "content": system_prompt})
            if prompt:
                final_messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if group_id and group_id not in ("None", "your-group-id", ""):
            headers["Group"] = group_id

        # Build request payload
        payload = {
            "model": model,
            "messages": final_messages,
            "stream": False
        }

        # Add tools if provided (for function calling)
        if tools:
            payload["tools"] = tools
            self.logger.info(f"[MiniMax] Sending {len(tools)} tools to API")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{MINIMAX_BASE_URL}/v1/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data.get("choices", [{}])[0].get("message", {})

                    # Extract content
                    content = message.get("content", "")

                    # Extract tool calls if present (MiniMax uses tool_calls field)
                    tool_calls = message.get("tool_calls", [])

                    # Extract token usage
                    usage = data.get("usage", {})

                    self.logger.info(f"[MiniMax] Response: content_len={len(content)}, tool_calls={len(tool_calls)}, usage={usage.get('total_tokens', 0)} tok")

                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "usage": usage
                    }
                else:
                    # 提取 headers
                    resp_headers = {}
                    for k, v in response.headers.items():
                        resp_headers[k.lower()] = v

                    # Log the actual error response for debugging
                    error_body = response.text
                    print(f"[DEBUG] MiniMax API Error {response.status_code}: {error_body[:1000]}")

                    # Classify error type and recoverability
                    if response.status_code in (401, 403):
                        error_type = LLMErrorType.AUTH_ERROR
                        recoverable = False
                    elif response.status_code == 429:
                        error_type = LLMErrorType.RATE_LIMIT
                        recoverable = True
                    else:
                        error_type = LLMErrorType.API_ERROR
                        recoverable = True

                    raise LLMError(
                        error_type,
                        "minimax",
                        f"API returned {response.status_code}: {error_body[:500]}",
                        recoverable=recoverable,
                        status_code=response.status_code,
                        headers=resp_headers
                    )

        except httpx.HTTPError as e:
            error = self._classify_error(e, "minimax")
            raise error

    async def _deepseek_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        config,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call DeepSeek API with optional function calling support"""
        api_key = config.api_key
        model = config.model or "deepseek-chat"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "deepseek", "API key not configured", recoverable=False)

        if messages is not None:
            final_messages = messages if messages else []
        else:
            final_messages = []
            if system_prompt:
                final_messages.append({"role": "system", "content": system_prompt})
            final_messages.append({"role": "user", "content": prompt})

        # Build request payload
        payload = {
            "model": model,
            "messages": final_messages,
            "stream": False
        }

        # Add tools if provided (for function calling)
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data.get("choices", [{}])[0].get("message", {})
                    content = message.get("content", "")
                    tool_calls = message.get("tool_calls", [])
                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "usage": data.get("usage", {})
                    }
                else:
                    raise LLMError(
                        LLMErrorType.API_ERROR,
                        "deepseek",
                        f"API returned {response.status_code}",
                        recoverable=True,
                        status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            error = self._classify_error(e, "deepseek")
            raise error

    async def _qwen_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        config,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call Qwen (Alibaba) API with optional function calling support"""
        api_key = config.api_key
        model = config.model or "qwen-turbo"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "qwen", "API key not configured", recoverable=False)

        if messages is not None:
            final_messages = messages if messages else []
        else:
            final_messages = []
            if system_prompt:
                final_messages.append({"role": "system", "content": system_prompt})
            final_messages.append({"role": "user", "content": prompt})

        # Build request payload
        payload = {
            "model": model,
            "messages": final_messages,
            "stream": False
        }

        # Add tools if provided (for function calling)
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data.get("choices", [{}])[0].get("message", {})
                    content = message.get("content", "")
                    tool_calls = message.get("tool_calls", [])
                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "usage": data.get("usage", {})
                    }
                else:
                    raise LLMError(
                        LLMErrorType.API_ERROR,
                        "qwen",
                        f"API returned {response.status_code}",
                        recoverable=True,
                        status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            error = self._classify_error(e, "qwen")
            raise error

    async def _openai_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        config,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call OpenAI API with optional function calling support"""
        api_key = config.api_key
        model = config.model or "gpt-4o"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "openai", "API key not configured", recoverable=False)

        if messages is not None:
            final_messages = messages if messages else []
        else:
            final_messages = []
            if system_prompt:
                final_messages.append({"role": "system", "content": system_prompt})
            final_messages.append({"role": "user", "content": prompt})

        # Build request payload
        payload = {
            "model": model,
            "messages": final_messages,
            "stream": False
        }

        # Add tools if provided (for function calling)
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data.get("choices", [{}])[0].get("message", {})
                    content = message.get("content", "")
                    tool_calls = message.get("tool_calls", [])
                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "usage": data.get("usage", {})
                    }
                else:
                    raise LLMError(
                        LLMErrorType.API_ERROR,
                        "openai",
                        f"API returned {response.status_code}",
                        recoverable=True,
                        status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            error = self._classify_error(e, "openai")
            raise error

    async def _anthropic_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        config,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call Anthropic API with optional function calling support"""
        api_key = config.api_key
        model = config.model or "claude-3-5-sonnet-20241022"
        max_tokens = kwargs.get("max_tokens", 4096)

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "anthropic", "API key not configured", recoverable=False)

        # Anthropic uses messages array with role/content
        anthropic_messages = []
        if system_prompt:
            anthropic_messages.append({"role": "user", "content": f"System: {system_prompt}"})
        if messages is not None:
            anthropic_messages.extend(messages)
        else:
            anthropic_messages.append({"role": "user", "content": prompt})

        # Build request payload
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt or "",
            "messages": anthropic_messages
        }

        # Add tools if provided (for function calling - Anthropic uses tools parameter)
        if tools:
            payload["tools"] = tools

        # Determine stop_reason based on response
        stop_reason = "end_turn"

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    # Anthropic returns content as array
                    content_blocks = data.get("content", [])
                    content = ""
                    tool_calls = []
                    for block in content_blocks:
                        if block.get("type") == "text":
                            content += block.get("text", "")
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": block.get("input", {})
                                }
                            })

                    # Determine stop_reason based on response
                    if tool_calls:
                        stop_reason = "tool_use"

                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "stop_reason": stop_reason
                    }
                else:
                    raise LLMError(
                        LLMErrorType.API_ERROR,
                        "anthropic",
                        f"API returned {response.status_code}",
                        recoverable=True,
                        status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            error = self._classify_error(e, "anthropic")
            raise error

    async def _zhipu_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        config,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call Zhipu AI API with optional function calling support"""
        api_key = config.api_key
        model = config.model or "glm-4"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "zhipu", "API key not configured", recoverable=False)

        if messages is not None:
            final_messages = messages if messages else []
        else:
            final_messages = []
            if system_prompt:
                final_messages.append({"role": "system", "content": system_prompt})
            final_messages.append({"role": "user", "content": prompt})

        # Build request payload
        payload = {
            "model": model,
            "messages": final_messages,
            "stream": False
        }

        # Add tools if provided (for function calling)
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data.get("choices", [{}])[0].get("message", {})
                    content = message.get("content", "")
                    tool_calls = message.get("tool_calls", [])
                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "usage": data.get("usage", {})
                    }
                else:
                    raise LLMError(
                        LLMErrorType.API_ERROR,
                        "zhipu",
                        f"API returned {response.status_code}",
                        recoverable=True,
                        status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            error = self._classify_error(e, "zhipu")
            raise error

    async def _moonshot_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        config,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call Moonshot (Kimi) API with optional function calling support"""
        api_key = config.api_key
        model = config.model or "moonshot-v1-8k"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "moonshot", "API key not configured", recoverable=False)

        if messages is not None:
            final_messages = messages if messages else []
        else:
            final_messages = []
            if system_prompt:
                final_messages.append({"role": "system", "content": system_prompt})
            final_messages.append({"role": "user", "content": prompt})

        # Build request payload
        payload = {
            "model": model,
            "messages": final_messages,
            "stream": False
        }

        # Add tools if provided (for function calling)
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://api.moonshot.cn/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data.get("choices", [{}])[0].get("message", {})
                    content = message.get("content", "")
                    tool_calls = message.get("tool_calls", [])
                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "usage": data.get("usage", {})
                    }
                else:
                    raise LLMError(
                        LLMErrorType.API_ERROR,
                        "moonshot",
                        f"API returned {response.status_code}",
                        recoverable=True,
                        status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            error = self._classify_error(e, "moonshot")
            raise error

    # Streaming methods
    async def _minimax_complete_stream(
        self,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        content_callback=None,
        **kwargs
    ):
        """MiniMax streaming API"""
        api_key = config.api_key
        group_id = config.group_id
        model = config.model or "MiniMax-M2.7"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "minimax", "API key not configured", recoverable=False)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if group_id and group_id not in ("None", "your-group-id", ""):
            headers["Group"] = group_id

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", f"{MINIMAX_BASE_URL}/v1/chat/completions", headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.atext()
                        raise LLMError(
                            LLMErrorType.API_ERROR,
                            "minimax",
                            f"API returned {response.status_code}: {error_body[:500]}",
                            recoverable=True,
                            status_code=response.status_code
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                import json as json_lib
                                data = json_lib.loads(data_str)
                                choices = data.get("choices", [{}])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        if content_callback:
                                            await content_callback(content)
                                        yield content
                            except:
                                pass
        except httpx.HTTPError as e:
            raise self._classify_error(e, "minimax")

    async def _deepseek_complete_stream(
        self,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        content_callback=None,
        **kwargs
    ):
        """DeepSeek streaming API"""
        api_key = config.api_key
        model = config.model or "deepseek-chat"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "deepseek", "API key not configured", recoverable=False)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", "https://api.deepseek.com/chat/completions", headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }, json=payload) as response:
                    if response.status_code != 200:
                        raise LLMError(
                            LLMErrorType.API_ERROR,
                            "deepseek",
                            f"API returned {response.status_code}",
                            recoverable=True,
                            status_code=response.status_code
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                import json as json_lib
                                data = json_lib.loads(data_str)
                                choices = data.get("choices", [{}])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        if content_callback:
                                            await content_callback(content)
                                        yield content
                            except:
                                pass
        except httpx.HTTPError as e:
            raise self._classify_error(e, "deepseek")

    async def _openai_complete_stream(
        self,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        content_callback=None,
        **kwargs
    ):
        """OpenAI streaming API"""
        api_key = config.api_key
        model = config.model or "gpt-4o"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "openai", "API key not configured", recoverable=False)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", "https://api.openai.com/v1/chat/completions", headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }, json=payload) as response:
                    if response.status_code != 200:
                        raise LLMError(
                            LLMErrorType.API_ERROR,
                            "openai",
                            f"API returned {response.status_code}",
                            recoverable=True,
                            status_code=response.status_code
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                import json as json_lib
                                data = json_lib.loads(data_str)
                                choices = data.get("choices", [{}])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        if content_callback:
                                            await content_callback(content)
                                        yield content
                            except:
                                pass
        except httpx.HTTPError as e:
            raise self._classify_error(e, "openai")

    async def _anthropic_complete_stream(
        self,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        content_callback=None,
        **kwargs
    ):
        """Anthropic streaming API - uses SSE format"""
        api_key = config.api_key
        model = config.model or "claude-3-5-sonnet-20241022"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "anthropic", "API key not configured", recoverable=False)

        # Build messages for Anthropic format
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                anthropic_messages.append({"role": "user", "content": f"[System] {content}"})
            else:
                anthropic_messages.append({"role": role, "content": content})

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "stream": True
        }

        if tools:
            # Convert tools to Anthropic format (unwrap OpenAI function wrapper)
            anthropic_tools = []
            for tool in tools:
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name", tool.get("name", "")),
                    "description": func.get("description", tool.get("description", "")),
                    "input_schema": func.get("parameters", tool.get("parameters", {}))
                })
            payload["tools"] = anthropic_tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                }, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.atext()
                        raise LLMError(
                            LLMErrorType.API_ERROR,
                            "anthropic",
                            f"API returned {response.status_code}: {error_body[:500]}",
                            recoverable=True,
                            status_code=response.status_code
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                import json as json_lib
                                data = json_lib.loads(data_str)
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        content = delta.get("text", "")
                                        if content:
                                            if content_callback:
                                                await content_callback(content)
                                            yield content
                            except:
                                pass
        except httpx.HTTPError as e:
            raise self._classify_error(e, "anthropic")

    # ==================== Structured Event Streaming ====================

    async def _minimax_stream_events(
        self,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        event_callback=None,
        max_tokens: int = 4096,
        **kwargs
    ):
        """MiniMax streaming with structured events"""
        api_key = config.api_key
        group_id = config.group_id
        model = config.model or "MiniMax-M2.7"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "minimax", "API key not configured", recoverable=False)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if group_id and group_id not in ("None", "your-group-id", ""):
            headers["Group"] = group_id

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", f"{MINIMAX_BASE_URL}/v1/chat/completions", headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.atext()
                        raise LLMError(
                            LLMErrorType.API_ERROR,
                            "minimax",
                            f"API returned {response.status_code}: {error_body[:500]}",
                            recoverable=True,
                            status_code=response.status_code
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                yield {"type": "message_end", "stop_reason": "end_turn"}
                                break
                            try:
                                import json as json_lib
                                data = json_lib.loads(data_str)
                                choices = data.get("choices", [{}])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    # Content delta
                                    content = delta.get("content", "")
                                    if content:
                                        yield {"type": "content_delta", "content": content}
                                        if event_callback:
                                            await event_callback({"type": "content_delta", "content": content})
                                    # Tool calls
                                    tool_calls = delta.get("tool_calls", [])
                                    for tc in tool_calls:
                                        yield {"type": "tool_use", **tc}
                                        if event_callback:
                                            await event_callback({"type": "tool_use", **tc})
                            except:
                                pass
        except httpx.HTTPError as e:
            raise self._classify_error(e, "minimax")

    async def _deepseek_stream_events(
        self,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        event_callback=None,
        **kwargs
    ):
        """DeepSeek streaming with structured events"""
        api_key = config.api_key
        model = config.model or "deepseek-chat"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "deepseek", "API key not configured", recoverable=False)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", "https://api.deepseek.com/chat/completions", headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }, json=payload) as response:
                    if response.status_code != 200:
                        raise LLMError(
                            LLMErrorType.API_ERROR,
                            "deepseek",
                            f"API returned {response.status_code}",
                            recoverable=True,
                            status_code=response.status_code
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                yield {"type": "message_end", "stop_reason": "end_turn"}
                                break
                            try:
                                import json as json_lib
                                data = json_lib.loads(data_str)
                                choices = data.get("choices", [{}])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield {"type": "content_delta", "content": content}
                                        if event_callback:
                                            await event_callback({"type": "content_delta", "content": content})
                                    tool_calls = delta.get("tool_calls", [])
                                    for tc in tool_calls:
                                        yield {"type": "tool_use", **tc}
                                        if event_callback:
                                            await event_callback({"type": "tool_use", **tc})
                            except:
                                pass
        except httpx.HTTPError as e:
            raise self._classify_error(e, "deepseek")

    async def _openai_stream_events(
        self,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        event_callback=None,
        **kwargs
    ):
        """OpenAI streaming with structured events"""
        api_key = config.api_key
        model = config.model or "gpt-4o"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "openai", "API key not configured", recoverable=False)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", "https://api.openai.com/v1/chat/completions", headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }, json=payload) as response:
                    if response.status_code != 200:
                        raise LLMError(
                            LLMErrorType.API_ERROR,
                            "openai",
                            f"API returned {response.status_code}",
                            recoverable=True,
                            status_code=response.status_code
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                yield {"type": "message_end", "stop_reason": "end_turn"}
                                break
                            try:
                                import json as json_lib
                                data = json_lib.loads(data_str)
                                choices = data.get("choices", [{}])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield {"type": "content_delta", "content": content}
                                        if event_callback:
                                            await event_callback({"type": "content_delta", "content": content})
                                    tool_calls = delta.get("tool_calls", [])
                                    for tc in tool_calls:
                                        yield {"type": "tool_use", **tc}
                                        if event_callback:
                                            await event_callback({"type": "tool_use", **tc})
                            except:
                                pass
        except httpx.HTTPError as e:
            raise self._classify_error(e, "openai")

    async def _anthropic_stream_events(
        self,
        config,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        event_callback=None,
        max_tokens: int = 4096,
        **kwargs
    ):
        """Anthropic streaming with structured events"""
        api_key = config.api_key
        model = config.model or "claude-3-5-sonnet-20241022"

        if not api_key:
            raise LLMError(LLMErrorType.AUTH_ERROR, "anthropic", "API key not configured", recoverable=False)

        # Build messages for Anthropic format
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                anthropic_messages.append({"role": "user", "content": f"[System] {content}"})
            else:
                anthropic_messages.append({"role": role, "content": content})

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "stream": True
        }

        if tools:
            anthropic_tools = []
            for tool in tools:
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name", tool.get("name", "")),
                    "description": func.get("description", tool.get("description", "")),
                    "input_schema": func.get("parameters", tool.get("parameters", {}))
                })
            payload["tools"] = anthropic_tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                }, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.atext()
                        raise LLMError(
                            LLMErrorType.API_ERROR,
                            "anthropic",
                            f"API returned {response.status_code}: {error_body[:500]}",
                            recoverable=True,
                            status_code=response.status_code
                        )

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                yield {"type": "message_end", "stop_reason": "end_turn"}
                                break
                            try:
                                import json as json_lib
                                data = json_lib.loads(data_str)
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        content = delta.get("text", "")
                                        if content:
                                            yield {"type": "content_delta", "content": content}
                                            if event_callback:
                                                await event_callback({"type": "content_delta", "content": content})
                                    elif delta.get("type") == "input_json_delta":
                                        # Tool use streaming
                                        content = delta.get("partial_json", "")
                                        if content:
                                            yield {"type": "tool_use_delta", "content": content}
                                            if event_callback:
                                                await event_callback({"type": "tool_use_delta", "content": content})
                                elif data.get("type") == "message_delta":
                                    # Check for stop reason
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "message_stop":
                                        yield {"type": "message_end", "stop_reason": "end_turn"}
                            except:
                                pass
        except httpx.HTTPError as e:
            raise self._classify_error(e, "anthropic")

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers"""
        status = {}
        for provider_id in LLM_PROVIDERS.keys():
            circuit = self._get_circuit(provider_id)
            config = runtime_config.providers.get(provider_id)
            status[provider_id] = {
                "state": circuit.state.value,
                "circuit_status": circuit.get_status(),
                "failure_count": circuit.failure_count,
                "has_api_key": bool(config.api_key if config else None),
                "current_model": config.model if config else None
            }
        return status

    def reset_provider(self, provider: str):
        """Reset a provider's circuit breaker"""
        circuit = self._get_circuit(provider)
        circuit.state = CircuitState.CLOSED
        circuit.failure_count = 0
        circuit.last_failure_time = None
        circuit.test_attempts = 0


# Singleton instance
llm_service = LLMService()


async def get_llm_response(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for getting LLM responses with error handling"""
    return await llm_service.complete(prompt, system_prompt)