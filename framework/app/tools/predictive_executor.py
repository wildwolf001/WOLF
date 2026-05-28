"""CBR 预测式执行器 — MCP-Cosmos 启发 (IBM, arXiv:2605.09131)"""
import hashlib
import time
from typing import Optional


class PredictiveToolExecutor:
    """基于历史记录的预测式执行 (CBR: Case-Based Reasoning)"""

    def __init__(self):
        self._history: dict = {}  # SHA256(input) -> (result, timestamp)

    def _hash(self, tool_name: str, params: dict) -> str:
        raw = tool_name + str(sorted(params.items()))
        return hashlib.sha256(raw.encode()).hexdigest()

    def predict(self, tool_name: str, params: dict, confidence_threshold: float = 0.85) -> Optional[dict]:
        """预测工具调用结果"""
        key = self._hash(tool_name, params)
        entry = self._history.get(key)
        if not entry:
            return None

        elapsed = time.time() - entry["timestamp"]
        # 48h 时效衰减
        freshness = max(0, 1.0 - elapsed / (48 * 3600))
        # 频率因子
        frequency = min(1.0, entry.get("count", 1) / 3)

        confidence = freshness * 0.6 + frequency * 0.4
        if confidence >= confidence_threshold:
            return {"result": entry["result"], "confidence": confidence, "from_cache": True}
        return None

    def record(self, tool_name: str, params: dict, result: Any):
        key = self._hash(tool_name, params)
        existing = self._history.get(key)
        self._history[key] = {
            "result": result,
            "timestamp": time.time(),
            "count": (existing.get("count", 0) + 1) if existing else 1
        }

    def invalidate(self, tool_name: str = None):
        """刷新缓存 (写操作后调用)"""
        if tool_name:
            keys = [k for k in self._history if k.startswith(tool_name)]
            for k in keys:
                del self._history[k]
        else:
            self._history.clear()
