"""
LLM Service - Unified interface for multiple LLM providers with error handling and circuit breaker
Supports: MiniMax, DeepSeek, Qwen, OpenAI, Anthropic, Zhipu, Moonshot
"""
import httpx
import asyncio
import time
from typing import Optional, Dict, Any, List
from enum import Enum
from app.core.runtime_config import runtime_config, LLM_PROVIDERS


class LLMErrorType(Enum):
    """LLM error types"""
    API_ERROR = "API_ERROR"           # Network, timeout, 5xx
    AUTH_ERROR = "AUTH_ERROR"         # 401, 403
    RATE_LIMIT = "RATE_LIMIT"        # 429
    MODEL_ERROR = "MODEL_ERROR"       # 406, model not supported
    UNKNOWN = "UNKNOWN"


class LLMError(Exception):
    """Custom LLM error with structured information"""
    def __init__(
        self,
        error_type: LLMErrorType,
        provider: str,
        message: str,
        recoverable: bool = True,
        status_code: Optional[int] = None
    ):
        self.error_type = error_type
        self.provider = provider
        self.message = message
        self.recoverable = recoverable
        self.status_code = status_code
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

    def _classify_error(self, e: Exception, provider: str, status_code: Optional[int] = None) -> LLMError:
        """Classify error type from exception"""
        if isinstance(e, httpx.HTTPError):
            if status_code:
                if status_code == 401 or status_code == 403:
                    return LLMError(
                        LLMErrorType.AUTH_ERROR, provider,
                        f"认证失败: {str(e)}", recoverable=False, status_code=status_code
                    )
                elif status_code == 429:
                    return LLMError(
                        LLMErrorType.RATE_LIMIT, provider,
                        f"请求限流: {str(e)}", recoverable=True, status_code=status_code
                    )
                elif status_code == 406:
                    return LLMError(
                        LLMErrorType.MODEL_ERROR, provider,
                        f"模型不支持: {str(e)}", recoverable=True, status_code=status_code
                    )
                elif 500 <= status_code < 600:
                    return LLMError(
                        LLMErrorType.API_ERROR, provider,
                        f"服务器错误: {str(e)}", recoverable=True, status_code=status_code
                    )

            # Timeout or connection error
            if isinstance(e, httpx.TimeoutException):
                return LLMError(
                    LLMErrorType.API_ERROR, provider,
                    f"请求超时: {str(e)}", recoverable=True, status_code=status_code
                )
            return LLMError(
                LLMErrorType.API_ERROR, provider,
                f"API错误: {str(e)}", recoverable=True, status_code=status_code
            )

        return LLMError(
            LLMErrorType.UNKNOWN, provider,
            f"未知错误: {str(e)}", recoverable=False, status_code=status_code
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
        max_retries: int = 1,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a completion request with error handling and fallback.

        Args:
            prompt: The user's prompt (used if messages is not provided)
            system_prompt: Optional system prompt
            max_retries: Maximum retries per provider
            messages: Optional list of message dicts for multi-turn conversation
            tools: Optional list of tool definitions for function calling

        Returns:
            Dict with 'success', 'content', 'tool_calls', and optionally 'error' keys
        """
        last_error: Optional[LLMError] = None
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

            # Try this provider with retries
            for attempt in range(max_retries + 1):
                try:
                    result = await self._call_provider(provider, config, prompt, system_prompt, messages, tools, **kwargs)
                    circuit.record_success()
                    return {
                        "success": True,
                        "content": result.get("content", ""),
                        "tool_calls": result.get("tool_calls", []),
                        "provider": provider
                    }
                except LLMError as e:
                    last_error = e
                    circuit.record_failure()

                    # Non-recoverable errors - don't retry this provider
                    if not e.recoverable:
                        break

                    # Wait before retry (exponential backoff)
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)

                except Exception as e:
                    # Unknown error - classify and handle
                    circuit = self._get_circuit(provider)
                    llm_error = self._classify_error(e, provider)
                    circuit.record_failure()
                    last_error = llm_error

                    if not llm_error.recoverable:
                        break

                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)

        # All providers failed
        return {
            "success": False,
            "error": last_error,
            "content": None,
            "provider": None
        }

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
        if provider == "minimax":
            return await self._minimax_complete(prompt, system_prompt, config, messages, tools, **kwargs)
        elif provider == "deepseek":
            return await self._deepseek_complete(prompt, system_prompt, config, messages, tools, **kwargs)
        elif provider == "qwen":
            return await self._qwen_complete(prompt, system_prompt, config, messages, tools, **kwargs)
        elif provider == "openai":
            return await self._openai_complete(prompt, system_prompt, config, messages, tools, **kwargs)
        elif provider == "anthropic":
            return await self._anthropic_complete(prompt, system_prompt, config, messages, tools, **kwargs)
        elif provider == "zhipu":
            return await self._zhipu_complete(prompt, system_prompt, config, messages, tools, **kwargs)
        elif provider == "moonshot":
            return await self._moonshot_complete(prompt, system_prompt, config, messages, tools, **kwargs)
        else:
            raise LLMError(LLMErrorType.UNKNOWN, provider, f"Unknown provider: {provider}", recoverable=False)

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
        if group_id and group_id != "None":
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

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.minimaxi.com/v1/chat/completions",
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

                    return {
                        "content": content,
                        "tool_calls": tool_calls
                    }
                else:
                    # Log the actual error response for debugging
                    error_body = response.text
                    print(f"[DEBUG] MiniMax API Error {response.status_code}: {error_body[:1000]}")
                    raise LLMError(
                        LLMErrorType.API_ERROR,
                        "minimax",
                        f"API returned {response.status_code}: {error_body[:500]}",
                        recoverable=True,
                        status_code=response.status_code
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
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                        "tool_calls": tool_calls
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
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                        "tool_calls": tool_calls
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
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                        "tool_calls": tool_calls
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
            "max_tokens": 4096,
            "system": system_prompt or "",
            "messages": anthropic_messages
        }

        # Add tools if provided (for function calling - Anthropic uses tools parameter)
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                    return {
                        "content": content,
                        "tool_calls": tool_calls
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
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                        "tool_calls": tool_calls
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
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                        "tool_calls": tool_calls
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
