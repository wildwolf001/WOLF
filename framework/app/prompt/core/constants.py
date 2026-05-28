"""Prompt 系统常量"""
from enum import Enum

# ── 对标 CC SYSTEM_PROMPT_DYNAMIC_BOUNDARY ──
STATIC_DYNAMIC_BOUNDARY = "__STATIC_DYNAMIC_BOUNDARY__"

# ── 缓存 ──
DEFAULT_CACHE_SCOPE = "session"

# ── Compaction ──
COMPACTION_THRESHOLD = 0.8      # 上下文使用率 80% 触发压缩
MAX_RECENT_TURNS = 5             # 压缩时保留最近 5 轮
MAX_PINNED_FILES = 5             # 压缩时保留最近 5 个文件

# ── Feature Flag ──
DEFAULT_ROLLOUT_PERCENT = 10    # 默认 10% 流量灰度
FULL_ROLLOUT = 100

# ── Template ──
DEFAULT_JINJA_EXTENSIONS = ["jinja2.ext.do"]

# ── Version ──
VERSION_STORAGE_DIR = "wolf_data/prompts"
