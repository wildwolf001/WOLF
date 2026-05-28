"""跨 Skill 元分析 + 三级调度 — daily/weekly/monthly"""
from typing import Dict, List
from datetime import datetime, timedelta
from enum import Enum


class OptimizationSchedule(str, Enum):
    DAILY = "daily"      # 高频轻量优化 (token 调整、描述微调)
    WEEKLY = "weekly"     # 全量评估 (success_rate 分析)
    MONTHLY = "monthly"   # 元更新 (跨 Skill 模式发现)


class MetaUpdater:
    """跨 Skill 元分析器"""

    def __init__(self):
        self._skill_metrics: Dict[str, List[dict]] = {}
        self._schedule_log: Dict[str, datetime] = {}

    def record_metrics(self, skill_name: str, metrics: dict):
        if skill_name not in self._skill_metrics:
            self._skill_metrics[skill_name] = []
        self._skill_metrics[skill_name].append({
            "timestamp": datetime.now().isoformat(),
            **metrics
        })

    def get_due_tasks(self) -> List[OptimizationSchedule]:
        """检查哪些调度任务到期"""
        now = datetime.now()
        due = []

        last_daily = self._schedule_log.get("daily")
        if not last_daily or (now - last_daily) > timedelta(hours=24):
            due.append(OptimizationSchedule.DAILY)

        last_weekly = self._schedule_log.get("weekly")
        if not last_weekly or (now - last_weekly) > timedelta(days=7):
            due.append(OptimizationSchedule.WEEKLY)

        last_monthly = self._schedule_log.get("monthly")
        if not last_monthly or (now - last_monthly) > timedelta(days=30):
            due.append(OptimizationSchedule.MONTHLY)

        return due

    def analyze_cross_skill(self) -> dict:
        """跨 Skill 模式分析 (monthly 元更新)"""
        patterns = {}
        all_skills = list(self._skill_metrics.keys())
        for skill_name in all_skills:
            metrics = self._skill_metrics[skill_name]
            if metrics:
                recent = metrics[-10:]
                avg_success = sum(m.get("success_rate", 0) for m in recent) / len(recent)
                patterns[skill_name] = {
                    "avg_success_rate": round(avg_success, 3),
                    "total_records": len(metrics),
                    "trend": "improving" if avg_success > 0.8 else "stable" if avg_success > 0.6 else "needs_attention"
                }
        return patterns

    def mark_completed(self, schedule: OptimizationSchedule):
        self._schedule_log[schedule.value] = datetime.now()
