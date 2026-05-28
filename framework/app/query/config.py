"""
Query Configuration
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class QueryConfig:
    """Configuration for query engine"""

    max_turns: int = 30
    max_tokens: int = 8000
    temperature: float = 0.7
    top_p: float = 0.9
    stop_sequences: Optional[List[str]] = None
    timeout: float = 120.0  # seconds

    # Model settings
    model: str = "claude-sonnet-4-20250514"
    stream: bool = True

    # Tool settings
    max_parallel_tools: int = 5

    # Context settings
    max_context_tokens: int = 100000
    context_overflow_threshold: float = 0.9


DEFAULT_QUERY_CONFIG = QueryConfig()