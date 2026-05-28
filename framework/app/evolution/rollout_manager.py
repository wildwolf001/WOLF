"""灰度发布管理器 — DRAFT→CANARY→PARTIAL→FULL_RELEASE / ROLLED_BACK (AGP 协议)"""
from enum import Enum
from typing import Optional
from datetime import datetime


class RolloutStage(str, Enum):
    DRAFT = "draft"
    CANARY = "canary"             # 10% 流量
    PARTIAL_RELEASE = "partial"    # 50% 流量
    FULL_RELEASE = "full_release"
    ROLLED_BACK = "rolled_back"


class RolloutManager:
    """灰度发布管理器"""

    def __init__(self):
        self._stages: dict = {}

    def create_rollout(self, artifact_id: str, base_score: float = 0.0):
        self._stages[artifact_id] = {
            "stage": RolloutStage.DRAFT,
            "base_score": base_score,
            "canary_score": None,
            "started_at": datetime.now().isoformat(),
            "history": []
        }

    def promote(self, artifact_id: str, new_stage: RolloutStage, score: float = None):
        if artifact_id not in self._stages:
            return
        entry = self._stages[artifact_id]
        entry["history"].append({"from": entry["stage"].value, "to": new_stage.value, "at": datetime.now().isoformat()})
        entry["stage"] = new_stage
        if score is not None:
            entry["canary_score"] = score

    def should_rollback(self, artifact_id: str, current_score: float) -> bool:
        """当前评分比基线下降 >10% → 自动回滚"""
        if artifact_id not in self._stages:
            return False
        base = self._stages[artifact_id]["base_score"]
        return base > 0 and current_score < base * 0.9

    def get_stage(self, artifact_id: str) -> Optional[RolloutStage]:
        entry = self._stages.get(artifact_id)
        return entry["stage"] if entry else None

    def rollback(self, artifact_id: str):
        self.promote(artifact_id, RolloutStage.ROLLED_BACK)
