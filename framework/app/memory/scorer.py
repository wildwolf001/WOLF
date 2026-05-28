"""记忆重要性评分 — recency × frequency × surprise × outcome (四维评分)"""
import math
import time
from typing import List, Optional
from enum import Enum

class MemoryCategory(str, Enum):
    KEEP = "keep"
    REVIEW = "review"
    ARCHIVE = "archive"
    DELETE = "delete"

class MemoryScorer:
    """四维重要性评分器"""

    def __init__(self):
        self._usage_log: dict = {}  # memory_id -> [timestamps]

    def score(self, memory: dict, now: float = None) -> dict:
        """计算综合评分"""
        now = now or time.time()

        # 1. Recency: 最近使用时间 (指数衰减)
        last_used = memory.get("last_used", now - 86400)
        if isinstance(last_used, str):
            last_used = now - 86400
        recency = math.exp(-(now - last_used) / 86400)  # 24h 半衰

        # 2. Frequency: 被检索次数
        usage = self._usage_log.get(memory.get("id", ""), [])
        frequency = min(1.0, len(usage) / 10)

        # 3. Surprise: 与已有记忆的矛盾程度 (Bayesian surprise, 简化)
        surprise = memory.get("surprise_score", 0.0)

        # 4. Outcome: 关联任务的结果
        outcome = 1.0 if memory.get("outcome") == "success" else 0.5

        total = recency * 0.25 + frequency * 0.25 + surprise * 0.25 + outcome * 0.25
        return {
            "total": round(total, 4),
            "recency": round(recency, 4),
            "frequency": round(frequency, 4),
            "surprise": round(surprise, 4),
            "outcome": round(outcome, 4),
            "category": self.categorize(total).value
        }

    def categorize(self, score: float) -> MemoryCategory:
        if score >= 0.6:
            return MemoryCategory.KEEP
        elif score >= 0.3:
            return MemoryCategory.REVIEW
        elif score >= 0.1:
            return MemoryCategory.ARCHIVE
        return MemoryCategory.DELETE

    def record_usage(self, memory_id: str):
        if memory_id not in self._usage_log:
            self._usage_log[memory_id] = []
        self._usage_log[memory_id].append(time.time())
        # 只保留最近 50 次记录
        if len(self._usage_log[memory_id]) > 50:
            self._usage_log[memory_id] = self._usage_log[memory_id][-50:]

    def score_all(self, memories: list) -> list:
        """批量评分"""
        now = time.time()
        results = []
        for m in memories:
            mdict = m if isinstance(m, dict) else m.to_dict() if hasattr(m, 'to_dict') else {"id": getattr(m, 'id', ''), "content": str(m)}
            s = self.score(mdict, now)
            mdict["importance_score"] = s["total"]
            mdict["score_category"] = s["category"]
            results.append(mdict)
        return sorted(results, key=lambda x: x.get("importance_score", 0), reverse=True)
