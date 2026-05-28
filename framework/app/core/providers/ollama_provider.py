"""Ollama 本地模型 Provider"""
import aiohttp
from typing import AsyncGenerator, Dict, Any


class OllamaProvider:
    """Ollama 本地模型适配器"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:7b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, messages: list, **kwargs) -> dict:
        """同步完成请求"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 2048),
                }
            }
            async with session.post(f"{self.base_url}/api/chat", json=payload) as resp:
                data = await resp.json()
                return {
                    "content": data.get("message", {}).get("content", ""),
                    "model": self.model,
                    "usage": {
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                    }
                }

    async def stream_complete(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """流式完成请求"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 2048),
                }
            }
            async with session.post(f"{self.base_url}/api/chat", json=payload) as resp:
                async for line in resp.content:
                    if line:
                        try:
                            import json
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                yield chunk
                        except Exception:
                            continue
