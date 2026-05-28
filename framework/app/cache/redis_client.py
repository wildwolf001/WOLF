"""Redis 缓存层 — Session / Embedding / RateLimiter / TaskQueue"""
import hashlib
import time
from typing import Optional, Any
import asyncio


class RedisClient:
    """Redis 客户端封装 (支持降级到内存 dict)"""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self._redis = None
        self._memory: dict = {}  # 降级存储
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.Redis(host=host, port=port, db=db, decode_responses=True)
        except ImportError:
            pass

    @property
    def connected(self) -> bool:
        return self._redis is not None

    async def get(self, key: str) -> Optional[str]:
        if self._redis:
            return await self._redis.get(key)
        entry = self._memory.get(key)
        if entry and entry.get("expires", float("inf")) > time.time():
            return entry["value"]
        return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        if self._redis:
            await self._redis.set(key, value, ex=ttl)
        else:
            self._memory[key] = {"value": value, "expires": time.time() + ttl}

    async def delete(self, key: str):
        if self._redis:
            await self._redis.delete(key)
        else:
            self._memory.pop(key, None)

    async def incr(self, key: str) -> int:
        if self._redis:
            return await self._redis.incr(key)
        current = int(self._memory.get(key, {}).get("value", 0))
        current += 1
        self._memory[key] = {"value": str(current), "expires": float("inf")}
        return current


class SessionCache:
    """会话缓存 (1h TTL)"""
    def __init__(self, client: RedisClient):
        self._client = client

    async def get_session(self, session_id: str) -> Optional[str]:
        return await self._client.get(f"session:{session_id}")

    async def set_session(self, session_id: str, data: str, ttl: int = 3600):
        await self._client.set(f"session:{session_id}", data, ttl)


class EmbeddingCache:
    """Embedding 缓存 (24h TTL, SHA256 键)"""
    def __init__(self, client: RedisClient):
        self._client = client

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:32]

    async def get(self, text: str) -> Optional[str]:
        return await self._client.get(f"embed:{self._hash(text)}")

    async def set(self, text: str, vector_json: str, ttl: int = 86400):
        await self._client.set(f"embed:{self._hash(text)}", vector_json, ttl)


class RateLimiter:
    """滑动窗口限流"""
    def __init__(self, client: RedisClient):
        self._client = client

    async def check(self, key: str, max_requests: int = 100, window: int = 60) -> bool:
        """检查是否超限 → True=允许, False=超限"""
        count = await self._client.incr(f"rate:{key}")
        if count == 1:
            await self._client.set(f"rate:{key}", "1", window)
        return count <= max_requests


_client: Optional[RedisClient] = None

def get_redis_client(host: str = "localhost", port: int = 6379) -> RedisClient:
    global _client
    if _client is None:
        _client = RedisClient(host=host, port=port)
    return _client
