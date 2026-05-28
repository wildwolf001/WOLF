"""
A/B 测试框架 — 流量分流 + 收集结果 + 统计决策
"""
import json
import os
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from .core.schemas import ABTestConfig


class ABTestManager:
    """A/B 测试管理器"""

    def __init__(self, storage_dir: str = None):
        self._storage_dir = storage_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "wolf_data", "prompts", "ab_tests"
        )
        os.makedirs(self._storage_dir, exist_ok=True)
        self._active_tests: Dict[str, ABTestConfig] = {}
        self._results: Dict[str, Dict[str, List[dict]]] = {}  # test_name -> {variant: [metrics]}

    def create_test(self, config: ABTestConfig) -> str:
        """创建 A/B 测试 → 返回 test_id"""
        test_id = f"{config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._active_tests[test_id] = config
        self._results[test_id] = {"a": [], "b": []}
        return test_id

    def get_variant(self, test_id: str, session_id: str) -> Optional[str]:
        """为 session 分配 variant (一致性哈希)"""
        test = self._active_tests.get(test_id)
        if not test:
            return None
        bucket = int(hashlib.md5((test_id + session_id).encode()).hexdigest(), 16) % 100
        threshold = int(test.traffic_split * 100)
        return "b" if bucket < threshold else "a"

    def record_result(self, test_id: str, variant: str, metrics: dict):
        """记录一次测试结果"""
        if test_id not in self._results:
            return
        self._results[test_id][variant].append({
            "timestamp": datetime.now().isoformat(),
            **metrics
        })

    def decide(self, test_id: str) -> str:
        """决定: 采用 b (实验组) 还是回退到 a (对照组)"""
        test = self._active_tests.get(test_id)
        if not test:
            return "insufficient_data"

        results = self._results.get(test_id, {})
        samples_a = results.get("a", [])
        samples_b = results.get("b", [])

        if len(samples_a) < test.min_samples or len(samples_b) < test.min_samples:
            return "collecting"

        # 简化统计：比较 completion_rate 均值
        avg_a = sum(r.get("completion_rate", 0) for r in samples_a) / len(samples_a)
        avg_b = sum(r.get("completion_rate", 0) for r in samples_b) / len(samples_b)

        # B 组比 A 组好 >5% → 采用 B
        if avg_b > avg_a * 1.05:
            return "adopt_b"
        # B 组比 A 组差 >10% → 回退 A
        elif avg_b < avg_a * 0.9:
            return "rollback_a"
        else:
            return "continue_testing"

    def get_results(self, test_id: str) -> dict:
        """获取测试统计"""
        results = self._results.get(test_id, {})
        stats = {}
        for variant in ["a", "b"]:
            samples = results.get(variant, [])
            if samples:
                stats[variant] = {
                    "samples": len(samples),
                    "avg_completion_rate": sum(r.get("completion_rate", 0) for r in samples) / len(samples),
                    "avg_token_efficiency": sum(r.get("token_efficiency", 0) for r in samples) / len(samples),
                }
            else:
                stats[variant] = {"samples": 0}
        return stats

    def close_test(self, test_id: str):
        """关闭测试，保存结果"""
        path = os.path.join(self._storage_dir, f"{test_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "config": {
                    "name": self._active_tests[test_id].name,
                    "traffic_split": self._active_tests[test_id].traffic_split,
                },
                "results": self._results.get(test_id, {}),
                "decision": self.decide(test_id)
            }, f, ensure_ascii=False, indent=2)
        self._active_tests.pop(test_id, None)


_ab_manager: Optional[ABTestManager] = None


def get_ab_test_manager() -> ABTestManager:
    global _ab_manager
    if _ab_manager is None:
        _ab_manager = ABTestManager()
    return _ab_manager
