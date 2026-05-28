"""Sleep Consolidation — 睡眠整合引擎 (Claude Code Auto Dream 启发)"""
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from .cognitive import CognitiveMemoryLayer

CONSOLIDATION_INTERVAL = 6 * 3600  # 默认每 6 小时

class SleepConsolidation:
    """后台定时任务：聚类相似短期记忆 → 合并为精炼长期知识"""

    def __init__(self, interval_seconds: float = CONSOLIDATION_INTERVAL):
        self.interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._consolidated_count = 0

    async def start(self, memory_accessor):
        """启动后台整合循环 (在 lifespan 中调用)"""
        self._task = asyncio.create_task(self._run(memory_accessor))

    async def _run(self, memory_accessor):
        while True:
            await asyncio.sleep(self.interval)
            try:
                await self._consolidate(memory_accessor)
            except Exception as e:
                print(f"[SleepConsolidation] Error: {e}")

    async def _consolidate(self, memory_accessor):
        """执行一次整合"""
        memories = memory_accessor.get_recent_memories(hours=self.interval // 3600)
        if not memories or len(memories) < 2:
            return

        # 聚类: 按 memory_type + 时间窗口分组
        clusters: Dict[str, list] = {}
        for m in memories:
            mtype = getattr(m, "memory_type", "general")
            key = f"{mtype}_{datetime.now().strftime('%Y%m%d_%H')}"
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(m)

        # 合并每个聚类
        for key, group in clusters.items():
            if len(group) < 2:
                continue
            # 合并内容: 取最具体的描述
            merged_content = self._merge_content([getattr(m, "content", "") for m in group])
            # 取最高权重
            merged_weight = max(getattr(m, "weight", 1.0) for m in group)
            # 写入长期记忆
            if memory_accessor.write_long_term:
                memory_accessor.write_long_term(
                    content=merged_content,
                    weight=merged_weight,
                    source_type="consolidation",
                    original_count=len(group)
                )
            self._consolidated_count += len(group)

        self._last_run = datetime.now()

    def _merge_content(self, contents: List[str]) -> str:
        """合并多个记忆内容为一条摘要"""
        if len(contents) == 1:
            return contents[0]
        # 去重 + 按长度排序取最长
        unique = list(set(c for c in contents if c))
        unique.sort(key=len, reverse=True)
        if len(unique) == 1:
            return unique[0]
        return f"[Merged {len(unique)} memories] " + " | ".join(unique[:3])

    @property
    def stats(self) -> dict:
        return {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "consolidated_count": self._consolidated_count,
            "interval_hours": self.interval / 3600
        }

    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
