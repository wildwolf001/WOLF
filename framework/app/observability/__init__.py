"""WOLF LLM 可观测性 — LangFuse + Tracker + Cost"""
from .langfuse_client import LangFuseClient, get_langfuse_client
from .tracker import track_llm_call, StatsAggregator, get_stats_aggregator
from .cost import CostCalculator, BudgetConfig, get_cost_calculator

def setup_observability(config: dict = None):
    config = config or {}
    client = get_langfuse_client(config.get("langfuse", {}))
    return {"langfuse_ready": client.is_connected}

__all__ = [
    "LangFuseClient", "get_langfuse_client",
    "track_llm_call", "StatsAggregator", "get_stats_aggregator",
    "CostCalculator", "BudgetConfig", "get_cost_calculator",
    "setup_observability",
]
