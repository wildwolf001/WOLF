"""认知记忆层 — Ebbinghaus 遗忘曲线 + 五层记忆层级 (ZenBrain 启发, arXiv:2604.23878)"""
import math
import time
from enum import Enum

class CognitiveMemoryLayer(str, Enum):
    WORKING = "working"         # 当前会话窗口
    SHORT_TERM = "short_term"   # SQLite, 最近 N 天
    EPISODIC = "episodic"       # 向量库, 长期
    SEMANTIC = "semantic"       # 知识图谱, 抽象规则
    PROCEDURAL = "procedural"   # 有效工作流模板

# 半衰期配置 (小时) — 按记忆类型
HALF_LIFE = {
    "user": 720,        # 30天
    "feedback": 2160,    # 90天
    "project": 168,      # 7天
    "reference": 1440,   # 60天
}
DEFAULT_HALF_LIFE = 168  # 默认 7天

class EbbinghausDecay:
    """遗忘曲线引擎: weight = initial * e^(-t / half_life)"""

    def __init__(self, half_life_hours: float = DEFAULT_HALF_LIFE):
        self.half_life = half_life_hours

    def weight(self, initial: float, elapsed_hours: float) -> float:
        if self.half_life <= 0:
            return initial
        return initial * math.exp(-elapsed_hours / self.half_life)

    def apply(self, memories: list, now: float = None) -> list:
        """对记忆列表应用衰减"""
        now = now or time.time()
        for m in memories:
            created = getattr(m, "created_at", now - 3600)
            if isinstance(created, str):
                created = now - 3600
            elapsed = (now - created) / 3600
            mtype = getattr(m, "memory_type", "project")
            half_life = HALF_LIFE.get(mtype, DEFAULT_HALF_LIFE)
            decay = EbbinghausDecay(half_life)
            m.weight = decay.weight(getattr(m, "weight", 1.0), elapsed)
        return memories

    @classmethod
    def for_type(cls, memory_type: str) -> "EbbinghausDecay":
        return cls(HALF_LIFE.get(memory_type, DEFAULT_HALF_LIFE))


def infer_cognitive_layer(memory: dict) -> CognitiveMemoryLayer:
    """推断记忆应归属哪一层"""
    weight = memory.get("weight", 1.0)
    review_count = memory.get("review_count", 0)
    mtype = memory.get("memory_type", "project")

    if mtype == "feedback":
        return CognitiveMemoryLayer.SEMANTIC
    if review_count >= 5 and weight > 0.5:
        return CognitiveMemoryLayer.EPISODIC
    if review_count >= 10:
        return CognitiveMemoryLayer.SEMANTIC
    if weight > 0.3:
        return CognitiveMemoryLayer.SHORT_TERM
    return CognitiveMemoryLayer.WORKING
