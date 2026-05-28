"""LLM 调用追踪装饰器 + 统计聚合器"""
import time
import functools
from typing import Dict, List, Optional
from datetime import datetime


class StatsAggregator:
    """滑动窗口统计聚合器 (窗口 2000 条)"""

    def __init__(self, window_size: int = 2000):
        self._window_size = window_size
        self._records: List[dict] = []

    def record(self, model: str, input_tokens: int, output_tokens: int, latency_ms: float, success: bool):
        self._records.append({
            "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens,
            "latency_ms": latency_ms, "success": success, "time": datetime.now().isoformat()
        })
        if len(self._records) > self._window_size:
            self._records = self._records[-self._window_size:]

    def stats_by_model(self) -> dict:
        models = {}
        for r in self._records:
            m = r["model"]
            if m not in models:
                models[m] = {"calls": 0, "input": 0, "output": 0, "total_latency": 0, "failures": 0}
            models[m]["calls"] += 1
            models[m]["input"] += r["input_tokens"]
            models[m]["output"] += r["output_tokens"]
            models[m]["total_latency"] += r["latency_ms"]
            if not r["success"]:
                models[m]["failures"] += 1
        for m in models:
            s = models[m]
            s["avg_latency_ms"] = round(s["total_latency"] / s["calls"], 1)
            s["success_rate"] = round((s["calls"] - s["failures"]) / s["calls"] * 100, 1)
        return models

    def total_stats(self) -> dict:
        return {
            "total_calls": len(self._records),
            "total_input_tokens": sum(r["input_tokens"] for r in self._records),
            "total_output_tokens": sum(r["output_tokens"] for r in self._records),
            "by_model": self.stats_by_model()
        }


_aggregator: Optional[StatsAggregator] = None

def get_stats_aggregator() -> StatsAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = StatsAggregator()
    return _aggregator


def track_llm_call(func=None, *, model_param: str = "model"):
    """装饰器：自动记录 LLM 调用到 StatsAggregator"""
    def decorator(f):
        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await f(*args, **kwargs)
                latency = (time.time() - start) * 1000
                model = kwargs.get(model_param, "unknown")
                # 估算 Token (粗略)
                input_text = str(kwargs.get("messages", ""))
                output_text = str(result)[:500]
                get_stats_aggregator().record(
                    model=model,
                    input_tokens=len(input_text) // 3,
                    output_tokens=len(output_text) // 3,
                    latency_ms=latency,
                    success=True
                )
                return result
            except Exception as e:
                latency = (time.time() - start) * 1000
                get_stats_aggregator().record(
                    model=kwargs.get(model_param, "unknown"),
                    input_tokens=0, output_tokens=0, latency_ms=latency, success=False
                )
                raise

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = f(*args, **kwargs)
                latency = (time.time() - start) * 1000
                get_stats_aggregator().record(
                    model=kwargs.get(model_param, "unknown"),
                    input_tokens=len(str(kwargs.get("messages", ""))) // 3,
                    output_tokens=len(str(result)[:500]) // 3,
                    latency_ms=latency, success=True
                )
                return result
            except Exception:
                latency = (time.time() - start) * 1000
                get_stats_aggregator().record(
                    model=kwargs.get(model_param, "unknown"),
                    input_tokens=0, output_tokens=0, latency_ms=latency, success=False
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(f):
            return async_wrapper
        return sync_wrapper

    if func is not None:
        return decorator(func)
    return decorator
