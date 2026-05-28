"""
Retry Configuration - 对齐 cc-haha 的环境变量配置

集中管理 LLM 调用重试相关的所有配置参数
"""

import os


# ==================== 重试次数配置 ====================

# 最大重试次数 (cc-haha DEFAULT_MAX_RETRIES = 10)
MAX_RETRIES = int(os.getenv("WOLF_LLM_MAX_RETRIES", "10"))

# 529 错误专用最大重试次数 (cc-haha MAX_529_RETRIES = 3)
MAX_529_RETRIES = int(os.getenv("WOLF_LLM_MAX_529_RETRIES", "3"))


# ==================== 延迟配置 ====================

# 基础延迟 (ms) (cc-haha BASE_DELAY_MS = 500)
BASE_DELAY_MS = int(os.getenv("WOLF_LLM_BASE_DELAY_MS", "500"))

# 最大延迟上限 (ms) (cc-haha MAX_DELAY_MS = 32000)
MAX_DELAY_MS = int(os.getenv("WOLF_LLM_MAX_DELAY_MS", "32000"))

# 短等待阈值 (ms) - retry-after 小于此值认为是短等待，直接重试
SHORT_RETRY_THRESHOLD_MS = int(os.getenv("WOLF_LLM_SHORT_RETRY_THRESHOLD_MS", "20000"))

# 最小 cooldown 时间 (ms) - 10分钟
MIN_COOLDOWN_MS = int(os.getenv("WOLF_LLM_MIN_COOLDOWN_MS", str(10 * 60 * 1000)))


# ==================== Persistent Retry 配置 ====================

# Persistent retry 最大退避时间 (ms) - 5分钟
# cc-haha: PERSISTENT_MAX_BACKOFF_MS = 5 * 60 * 1000
PERSISTENT_MAX_BACKOFF_MS = int(os.getenv("WOLF_LLM_PERSISTENT_MAX_BACKOFF_MS", str(5 * 60 * 1000)))

# Persistent retry 重置上限 (ms) - 6小时
# cc-haha: PERSISTENT_RESET_CAP_MS = 6 * 60 * 60 * 1000
PERSISTENT_RESET_CAP_MS = int(os.getenv("WOLF_LLM_PERSISTENT_RESET_CAP_MS", str(6 * 60 * 60 * 1000)))

# Heartbeat 间隔 (ms) - 30秒
# cc-haha: HEARTBEAT_INTERVAL_MS = 30_000
HEARTBEAT_INTERVAL_MS = int(os.getenv("WOLF_LLM_HEARTBEAT_INTERVAL_MS", "30000"))


# ==================== Fast Mode 配置 ====================

# Fast mode fallback hold 时间 (ms) - 30分钟
# cc-haha: DEFAULT_FAST_MODE_FALLBACK_HOLD_MS = 30 * 60 * 1000
DEFAULT_FAST_MODE_FALLBACK_HOLD_MS = int(os.getenv("WOLF_LLM_FAST_MODE_FALLBACK_HOLD_MS", str(30 * 60 * 1000)))


# ==================== 其他配置 ====================

# 是否启用 persistent retry (unattended 模式)
UNATTENDED_RETRY = os.getenv("WOLF_LLM_UNATTENDED_RETRY", "false").lower() == "true"

# 最小输出 tokens (cc-haha FLOOR_OUTPUT_TOKENS = 3000)
FLOOR_OUTPUT_TOKENS = int(os.getenv("WOLF_LLM_FLOOR_OUTPUT_TOKENS", "3000"))


# ==================== 前台任务标识 ====================

# 前台任务类型 - 这些任务在 529 时会重试
# cc-haha: FOREGROUND_529_RETRY_SOURCES
FOREGROUND_529_RETRY_SOURCES = {
    'repl_main_thread',
    'repl_main_thread:outputStyle:custom',
    'repl_main_thread:outputStyle:Explanatory',
    'repl_main_thread:outputStyle:Learning',
    'sdk',
    'agent:custom',
    'agent:default',
    'agent:builtin',
    'compact',
    'hook_agent',
    'hook_prompt',
    'verification_agent',
    'side_question',
    'auto_mode',
}


def get_retry_config() -> dict:
    """获取完整的重试配置"""
    return {
        "max_retries": MAX_RETRIES,
        "max_529_retries": MAX_529_RETRIES,
        "base_delay_ms": BASE_DELAY_MS,
        "max_delay_ms": MAX_DELAY_MS,
        "short_retry_threshold_ms": SHORT_RETRY_THRESHOLD_MS,
        "min_cooldown_ms": MIN_COOLDOWN_MS,
        "persistent_max_backoff_ms": PERSISTENT_MAX_BACKOFF_MS,
        "persistent_reset_cap_ms": PERSISTENT_RESET_CAP_MS,
        "heartbeat_interval_ms": HEARTBEAT_INTERVAL_MS,
        "unattended_retry": UNATTENDED_RETRY,
        "floor_output_tokens": FLOOR_OUTPUT_TOKENS,
        "foreground_sources": list(FOREGROUND_529_RETRY_SOURCES),
    }