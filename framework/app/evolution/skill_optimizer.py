"""Skill 自动优化器 — TextualLR + ReflectionMinibatch (SkillOpt, Microsoft 2026)"""
from typing import List, Optional
from .versioned_artifact import VersionedArtifact, ArtifactStore


class SkillOptimizer:
    """基于执行轨迹的 Skill 自动优化器"""

    def __init__(self, store: ArtifactStore = None):
        self._store = store or ArtifactStore()
        self._trajectory_buffer: list = []
        self._minibatch_size = 20  # ReflectionMinibatch

    def record_trajectory(self, skill_name: str, success: bool, tokens_used: int, error: str = ""):
        self._trajectory_buffer.append({
            "skill_name": skill_name,
            "success": success, "tokens_used": tokens_used, "error": error
        })

    def should_optimize(self) -> bool:
        """积累足够轨迹 → 触发优化"""
        return len(self._trajectory_buffer) >= self._minibatch_size

    def analyze(self) -> dict:
        """分析失败轨迹，提取共性"""
        if not self._trajectory_buffer:
            return {"status": "no_data"}

        by_skill = {}
        for t in self._trajectory_buffer:
            name = t["skill_name"]
            if name not in by_skill:
                by_skill[name] = {"total": 0, "successes": 0, "failures": 0, "errors": [], "tokens": []}
            by_skill[name]["total"] += 1
            by_skill[name]["tokens"].append(t["tokens_used"])
            if t["success"]:
                by_skill[name]["successes"] += 1
            else:
                by_skill[name]["failures"] += 1
                if t["error"]:
                    by_skill[name]["errors"].append(t["error"])

        result = {}
        for name, stats in by_skill.items():
            success_rate = stats["successes"] / stats["total"] if stats["total"] > 0 else 0
            avg_tokens = sum(stats["tokens"]) / len(stats["tokens"]) if stats["tokens"] else 0
            result[name] = {
                "success_rate": round(success_rate, 3),
                "avg_tokens": round(avg_tokens, 1),
                "needs_optimization": success_rate < 0.7,
                "top_errors": list(set(stats["errors"]))[:3]
            }
        return result

    def propose_improvement(self, skill_name: str, current_content: str, analysis: dict) -> str:
        """生成优化建议 (TextualLR 控制修改幅度)"""
        stats = analysis.get(skill_name, {})
        success_rate = stats.get("success_rate", 1.0)
        textual_lr = 0.3 if success_rate < 0.5 else 0.1 if success_rate < 0.7 else 0.03
        max_chars = max(10, int(len(current_content) * textual_lr))

        improvement = f"\n<!-- Auto-optimized: success_rate={success_rate:.2f}, lr={textual_lr:.2f} -->\n"
        if stats.get("top_errors"):
            improvement += "## Common Failure Modes\n"
            for err in stats["top_errors"]:
                improvement += f"- {err}\n"
        return improvement[:max_chars + len(improvement) - max_chars] if len(improvement) > max_chars + 100 else improvement

    def clear_buffer(self):
        self._trajectory_buffer = []
