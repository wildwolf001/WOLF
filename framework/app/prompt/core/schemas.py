"""
Prompt 系统核心数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime


class CacheScope(str, Enum):
    GLOBAL = "global"      # 跨会话/跨用户复用 (对标 CC global cache scope)
    SESSION = "session"    # 当前会话内复用
    DYNAMIC = "dynamic"    # 每轮重新计算 (对标 CC DANGEROUS_uncachedSystemPromptSection)

class LayerType(str, Enum):
    ROLE = "role"          # 角色定义
    RULES = "rules"         # 行为规则
    CONTEXT = "context"    # 上下文信息
    OUTPUT = "output"      # 输出格式

class SessionMode(str, Enum):
    DEFAULT = "default"
    REPL = "repl"

@dataclass
class PromptVersion:
    """Prompt 语义化版本"""
    name: str
    version: str                          # semver "v1.2.3"
    content: str
    parent_version: Optional[str] = None  # 回滚目标
    performance_score: float = 0.0
    changelog: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ABTestConfig:
    """A/B 测试配置"""
    name: str
    variant_a: str  # 对照组 Prompt
    variant_b: str  # 实验组 Prompt
    traffic_split: float = 0.5   # B 组流量比例
    min_samples: int = 50        # 最少样本数
    metrics: List[str] = field(default_factory=lambda: ["completion_rate", "token_efficiency"])

@dataclass
class FeatureFlag:
    """Feature Flag 配置 (对标 CC feature() 机制)"""
    name: str
    enabled: bool = False
    rollout_percent: int = 0     # 0-100
    description: str = ""

@dataclass
class CompactConfig:
    """上下文压缩配置"""
    threshold: float = 0.8        # 80% 上下文使用率触发
    keep_recent_turns: int = 5    # 保留最近 N 轮对话
    keep_pinned_files: int = 5    # 保留最近操作的 N 个文件内容
