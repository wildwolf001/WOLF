"""Skill 评估器 — 80/20 留出验证集 + 门控机制"""
from typing import List, Optional


class SkillEvaluator:
    """Skill 评估器：优化后准确率 >= 优化前 才允许发布"""

    def __init__(self, validation_ratio: float = 0.2):
        self._validation_ratio = validation_ratio
        self._baselines: dict = {}   # skill_name -> baseline_score
        self._evaluations: dict = {} # skill_name -> [scores]

    def set_baseline(self, skill_name: str, success_rate: float, avg_tokens: float = 0):
        self._baselines[skill_name] = {"success_rate": success_rate, "avg_tokens": avg_tokens}

    def evaluate(self, skill_name: str, success_rate: float, avg_tokens: float = 0) -> dict:
        """评估优化结果 vs 基线"""
        if skill_name not in self._evaluations:
            self._evaluations[skill_name] = []
        self._evaluations[skill_name].append({
            "success_rate": success_rate, "avg_tokens": avg_tokens
        })

        baseline = self._baselines.get(skill_name, {"success_rate": 1.0})
        passed = success_rate >= baseline["success_rate"]  # 门控：效果不下降

        return {
            "passed": passed,
            "baseline_success_rate": baseline["success_rate"],
            "current_success_rate": success_rate,
            "improvement": round(success_rate - baseline["success_rate"], 3),
            "gating_reason": "" if passed else f"success_rate dropped from {baseline['success_rate']} to {success_rate}"
        }

    def get_average(self, skill_name: str, last_n: int = 10) -> dict:
        """获取最近 N 次评估的平均值"""
        evals = self._evaluations.get(skill_name, [])[-last_n:]
        if not evals:
            return {"success_rate": 0, "samples": 0}
        return {
            "success_rate": round(sum(e["success_rate"] for e in evals) / len(evals), 3),
            "avg_tokens": round(sum(e["avg_tokens"] for e in evals) / len(evals), 1),
            "samples": len(evals)
        }
