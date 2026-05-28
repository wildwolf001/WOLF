"""LangFuse Trace 客户端 — LLM 调用链追踪"""
from typing import Optional, Dict, Any
from datetime import datetime


class LangFuseClient:
    """LangFuse API 封装，支持本地内存降级"""

    def __init__(self, public_key: str = None, secret_key: str = None, host: str = None):
        self._client = None
        self._traces: list = []  # 本地降级存储
        try:
            if public_key and secret_key:
                import langfuse
                self._client = langfuse.Langfuse(
                    public_key=public_key, secret_key=secret_key, host=host or "https://cloud.langfuse.com"
                )
        except ImportError:
            pass

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def create_trace(self, name: str, metadata: dict = None) -> Optional[str]:
        """创建 Trace"""
        trace_id = f"trace_{datetime.now().timestamp()}"
        if self._client:
            try:
                trace = self._client.trace(name=name, metadata=metadata)
                return trace.id
            except Exception:
                pass
        self._traces.append({"id": trace_id, "name": name, "metadata": metadata, "time": datetime.now().isoformat()})
        return trace_id

    def log_generation(self, trace_id: str, model: str, input_tokens: int, output_tokens: int,
                       latency_ms: float, success: bool = True, metadata: dict = None):
        """记录一次 LLM 调用"""
        entry = {
            "trace_id": trace_id, "model": model,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "latency_ms": latency_ms, "success": success, "metadata": metadata or {},
            "time": datetime.now().isoformat()
        }
        self._traces.append(entry)

    def get_stats(self, hours: int = 24) -> dict:
        """获取统计 (本地降级模式)"""
        cutoff = datetime.now().timestamp() - hours * 3600
        recent = [t for t in self._traces if t.get("time", "").startswith(str(datetime.now().date()))]
        models = {}
        for t in recent:
            m = t.get("model", "unknown")
            if m not in models:
                models[m] = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "failures": 0}
            models[m]["calls"] += 1
            models[m]["input_tokens"] += t.get("input_tokens", 0)
            models[m]["output_tokens"] += t.get("output_tokens", 0)
            if not t.get("success", True):
                models[m]["failures"] += 1
        return {"total_calls": len(recent), "models": models}


_client: Optional[LangFuseClient] = None

def get_langfuse_client(config: dict = None) -> LangFuseClient:
    global _client
    if _client is None:
        config = config or {}
        _client = LangFuseClient(
            public_key=config.get("public_key"),
            secret_key=config.get("secret_key"),
            host=config.get("host")
        )
    return _client
