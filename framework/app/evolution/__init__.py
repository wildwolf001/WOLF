"""WOLF 自我进化系统 — AGP 协议 (Stanford, arXiv:2604.15034)"""
from .versioned_artifact import VersionedArtifact, ArtifactStore
from .skill_optimizer import SkillOptimizer
from .tool_evolver import ToolDescOptimizer, ToolUsageAnalyzer
from .rollout_manager import RolloutManager

def setup_evolution_system():
    """在 lifespan 中调用"""
    return {"ready": True}

__all__ = [
    "VersionedArtifact", "ArtifactStore",
    "SkillOptimizer", "ToolDescOptimizer", "ToolUsageAnalyzer",
    "RolloutManager", "setup_evolution_system",
]
