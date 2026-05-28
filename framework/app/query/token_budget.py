"""
Token Budget Management
Manages token usage for queries
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TokenBudget:
    """Token budget tracker"""

    max_tokens: int
    used_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def remaining(self) -> int:
        return self.max_tokens - self.used_tokens

    @property
    def usage_ratio(self) -> float:
        if self.max_tokens == 0:
            return 0.0
        return self.used_tokens / self.max_tokens

    @property
    def is_exhausted(self) -> bool:
        return self.used_tokens >= self.max_tokens

    def add_prompt_tokens(self, count: int) -> None:
        """Add prompt tokens to the budget"""
        self.prompt_tokens += count
        self.used_tokens += count

    def add_completion_tokens(self, count: int) -> None:
        """Add completion tokens to the budget"""
        self.completion_tokens += count
        self.used_tokens += count

    def reset(self) -> None:
        """Reset the budget"""
        self.used_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0


class TokenBudgetManager:
    """
    Manages token budgets across queries and conversations.
    """

    def __init__(self, default_budget: int = 100000):
        self._default_budget = default_budget
        self._budgets: dict[str, TokenBudget] = {}

    def get_budget(self, session_id: str) -> TokenBudget:
        """Get or create budget for a session"""
        if session_id not in self._budgets:
            self._budgets[session_id] = TokenBudget(max_tokens=self._default_budget)
        return self._budgets[session_id]

    def create_session_budget(
        self,
        session_id: str,
        max_tokens: Optional[int] = None
    ) -> TokenBudget:
        """Create a new budget for a session"""
        budget = TokenBudget(max_tokens=max_tokens or self._default_budget)
        self._budgets[session_id] = budget
        return budget

    def release_budget(self, session_id: str) -> None:
        """Release a budget when session ends"""
        if session_id in self._budgets:
            del self._budgets[session_id]

    def get_total_usage(self) -> int:
        """Get total token usage across all sessions"""
        return sum(b.used_tokens for b in self._budgets.values())


# Global token budget manager
_token_budget_manager: Optional[TokenBudgetManager] = None


def get_token_budget_manager() -> TokenBudgetManager:
    """Get the global token budget manager"""
    global _token_budget_manager
    if _token_budget_manager is None:
        _token_budget_manager = TokenBudgetManager()
    return _token_budget_manager