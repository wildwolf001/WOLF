"""
WOLF Prompt Engineering System
对标 Claude Code prompt 架构 (cc-haha-main/src/constants/)
"""
from .core.schemas import (
    CacheScope, LayerType, SessionMode, PromptVersion, ABTestConfig, FeatureFlag
)
from .core.constants import STATIC_DYNAMIC_BOUNDARY
from .cache import SectionCache, get_section_cache
from .layers import PromptLayer, PromptAssembler
from .assembler import ConditionalAssembler
from .template import PromptTemplateEngine, get_template_engine
from .versioning import PromptVersioning, get_prompt_versioning
from .compact import CompactManager
from .feature_flags import FeatureFlagManager, get_feature_flag_manager
from .ab_test import ABTestManager, get_ab_test_manager


def init_prompt_system(config: dict = None):
    """在 main.py lifespan 中调用，初始化所有 Prompt 子系统"""
    config = config or {}

    # 初始化 Feature Flag (从 config.json 加载)
    fm = get_feature_flag_manager()
    fm.register_from_config(config.get("prompt_experiments", {}))

    # 初始化缓存
    cache = get_section_cache()

    return {
        "feature_flags": len(fm.list_all()),
        "cache_ready": True,
    }


__all__ = [
    "CacheScope", "LayerType", "SessionMode",
    "PromptVersion", "ABTestConfig", "FeatureFlag",
    "STATIC_DYNAMIC_BOUNDARY",
    "SectionCache", "get_section_cache",
    "PromptLayer", "PromptAssembler",
    "ConditionalAssembler",
    "PromptTemplateEngine", "get_template_engine",
    "PromptVersioning", "get_prompt_versioning",
    "CompactManager",
    "FeatureFlagManager", "get_feature_flag_manager",
    "ABTestManager", "get_ab_test_manager",
    "init_prompt_system",
]
