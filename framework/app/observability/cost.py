"""Token 成本计算 + 预算预警"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class BudgetConfig:
    daily_token_limit: int = 1_000_000
    daily_cost_limit: float = 50.0
    alert_threshold: float = 0.8

# 2026 参考定价 ($/1M tokens)
MODEL_PRICING: Dict[str, dict] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "qwen-turbo": {"input": 0.30, "output": 0.60},
    "minimax-m2": {"input": 0.50, "output": 2.00},
}

class CostCalculator:
    """LLM 调用成本计算器"""

    def __init__(self, config: BudgetConfig = None):
        self.config = config or BudgetConfig()
        self._daily_input = 0
        self._daily_output = 0
        self._daily_cost = 0.0

    def record(self, model: str, input_tokens: int, output_tokens: int):
        """记录一次调用"""
        pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 4.0})
        cost = (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]
        self._daily_input += input_tokens
        self._daily_output += output_tokens
        self._daily_cost += cost

    @property
    def token_usage_ratio(self) -> float:
        if self.config.daily_token_limit <= 0:
            return 0.0
        return (self._daily_input + self._daily_output) / self.config.daily_token_limit

    @property
    def cost_usage_ratio(self) -> float:
        if self.config.daily_cost_limit <= 0:
            return 0.0
        return self._daily_cost / self.config.daily_cost_limit

    @property
    def alert_level(self) -> str:
        """预警级别"""
        max_ratio = max(self.token_usage_ratio, self.cost_usage_ratio)
        if max_ratio >= 1.0:
            return "CRITICAL"
        if max_ratio >= self.config.alert_threshold:
            return "WARN"
        return "OK"

    def suggest_downgrade(self) -> str:
        """超预算时建议降级模型"""
        if self.alert_level in ("CRITICAL", "WARN"):
            return "deepseek-chat"
        return ""

    def reset_daily(self):
        self._daily_input = 0
        self._daily_output = 0
        self._daily_cost = 0.0

    @property
    def summary(self) -> dict:
        return {
            "daily_input_tokens": self._daily_input,
            "daily_output_tokens": self._daily_output,
            "daily_cost": round(self._daily_cost, 4),
            "token_ratio": round(self.token_usage_ratio, 2),
            "cost_ratio": round(self.cost_usage_ratio, 2),
            "alert": self.alert_level,
            "suggested_model": self.suggest_downgrade() if self.alert_level != "OK" else None
        }


_calculator: CostCalculator = None

def get_cost_calculator() -> CostCalculator:
    global _calculator
    if _calculator is None:
        _calculator = CostCalculator()
    return _calculator
