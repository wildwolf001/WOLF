"""
Cost Tracker Service
Tracks API usage and costs
"""
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class CostRecord:
    """A cost record"""
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    session_id: str


class CostTracker:
    """
    Tracks token usage and cost across sessions.
    """

    def __init__(self):
        self._records: list[CostRecord] = []
        self._session_costs: Dict[str, float] = {}

    def record(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> None:
        """Record a cost entry"""
        record = CostRecord(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            session_id=session_id
        )
        self._records.append(record)

        # Update session total
        if session_id not in self._session_costs:
            self._session_costs[session_id] = 0.0
        self._session_costs[session_id] += cost

    def get_session_cost(self, session_id: str) -> float:
        """Get total cost for a session"""
        return self._session_costs.get(session_id, 0.0)

    def get_total_cost(self) -> float:
        """Get total cost across all sessions"""
        return sum(r.cost for r in self._records)

    def get_total_tokens(self) -> tuple[int, int]:
        """Get total input and output tokens"""
        input_total = sum(r.input_tokens for r in self._records)
        output_total = sum(r.output_tokens for r in self._records)
        return input_total, output_total

    def get_recent_records(self, count: int = 10) -> list[CostRecord]:
        """Get recent cost records"""
        return self._records[-count:] if self._records else []


class CostTrackerService:
    """
    Service for tracking API costs.
    """

    # Approximate cost per 1M tokens (USD)
    COST_PER_MILLION = {
        "claude-sonnet-4-20250514": {
            "input": 3.0,
            "output": 15.0
        },
        "claude-opus-4-20250514": {
            "input": 15.0,
            "output": 75.0
        }
    }

    def __init__(self):
        self._tracker = CostTracker()

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for a request"""
        rates = self.COST_PER_MILLION.get(model, {"input": 3.0, "output": 15.0})
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        return input_cost + output_cost

    def record_usage(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Record usage and return cost"""
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        self._tracker.record(session_id, model, input_tokens, output_tokens, cost)
        return cost

    def get_session_cost(self, session_id: str) -> float:
        """Get cost for a session"""
        return self._tracker.get_session_cost(session_id)

    def get_total_cost(self) -> float:
        """Get total cost"""
        return self._tracker.get_total_cost()


# Global cost tracker service
_cost_tracker_service: Optional[CostTrackerService] = None


def get_cost_tracker_service() -> CostTrackerService:
    """Get the global cost tracker service"""
    global _cost_tracker_service
    if _cost_tracker_service is None:
        _cost_tracker_service = CostTrackerService()
    return _cost_tracker_service