"""
Token Estimation Service
Estimates token usage for prompts and completions
"""
from typing import List, Dict, Any, Optional
import re


class TokenEstimator:
    """
    Estimates token usage for text.
    Uses simple character-based estimation.
    """

    # Average tokens per character ratio for English
    TOKENS_PER_CHAR = 0.25

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self._model = model

    def estimate(self, text: str) -> int:
        """Estimate tokens for text"""
        if not text:
            return 0
        return int(len(text) * self.TOKENS_PER_CHAR) + 1

    def estimate_messages(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate tokens for a message list"""
        total = 0
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            # Add overhead for role markers
            total += self.estimate(role) + self.estimate(content)
        return total

    def estimate_tools(self, tools: List[Dict[str, Any]]) -> int:
        """Estimate tokens for tool definitions"""
        total = 0
        for tool in tools:
            tool_text = str(tool)
            total += self.estimate(tool_text)
        return total

    def estimate_system_prompt(self, prompt: str) -> int:
        """Estimate tokens for system prompt"""
        return self.estimate(prompt)


class TokenEstimationService:
    """
    Service for estimating token usage.
    """

    def __init__(self):
        self._estimator = TokenEstimator()

    def estimate_query(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        tools: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Estimate total tokens for a query"""
        msg_tokens = self._estimator.estimate_messages(messages)
        sys_tokens = self._estimator.estimate_system_prompt(system_prompt)
        tool_tokens = self._estimator.estimate_tools(tools)

        return {
            "messages": msg_tokens,
            "system": sys_tokens,
            "tools": tool_tokens,
            "total": msg_tokens + sys_tokens + tool_tokens
        }

    def get_estimator(self) -> TokenEstimator:
        """Get the underlying estimator"""
        return self._estimator


# Global estimation service
_estimation_service: Optional[TokenEstimationService] = None


def get_estimation_service() -> TokenEstimationService:
    """Get the global estimation service"""
    global _estimation_service
    if _estimation_service is None:
        _estimation_service = TokenEstimationService()
    return _estimation_service