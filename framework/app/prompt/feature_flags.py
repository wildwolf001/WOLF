"""
Feature Flag 灰度发布 — 对标 CC feature() 机制
基于 session_id 一致性哈希分流，支持 0-100% 灰度，A/B 实验管理
"""
import hashlib
from typing import Dict, Optional
from .core.schemas import FeatureFlag
from .core.constants import DEFAULT_ROLLOUT_PERCENT


class FeatureFlagManager:
    """Feature Flag 管理器"""

    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}

    def register(self, flag: FeatureFlag):
        self._flags[flag.name] = flag

    def register_from_config(self, config: dict):
        """从 config.json 加载: {"prompt_experiments": {...}}"""
        for name, cfg in config.get("prompt_experiments", {}).items():
            self._flags[name] = FeatureFlag(
                name=name,
                enabled=cfg.get("enabled", False),
                rollout_percent=cfg.get("rollout_percent", DEFAULT_ROLLOUT_PERCENT),
                description=cfg.get("description", "")
            )

    def is_enabled(self, flag_name: str, session_id: str) -> bool:
        """检查该 session 是否启用某 Feature Flag"""
        flag = self._flags.get(flag_name)
        if not flag or not flag.enabled:
            return False
        if flag.rollout_percent >= 100:
            return True
        if flag.rollout_percent <= 0:
            return False
        # 一致性哈希：同一 session 始终在同一分组
        bucket = int(hashlib.md5(session_id.encode()).hexdigest(), 16) % 100
        return bucket < flag.rollout_percent

    def get_enabled_flags(self, session_id: str) -> Dict[str, FeatureFlag]:
        """获取该 session 启用的所有 Feature Flag"""
        return {
            name: flag
            for name, flag in self._flags.items()
            if self.is_enabled(name, session_id)
        }

    def list_all(self) -> Dict[str, FeatureFlag]:
        return dict(self._flags)


_flag_manager: Optional[FeatureFlagManager] = None


def get_feature_flag_manager() -> FeatureFlagManager:
    global _flag_manager
    if _flag_manager is None:
        _flag_manager = FeatureFlagManager()
    return _flag_manager
