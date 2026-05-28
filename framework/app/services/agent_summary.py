"""
Agent Summary Service
Generates summaries of agent activity
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AgentSummary:
    """Agent activity summary"""
    session_id: str
    turn_count: int
    tool_count: int
    token_usage: int
    duration: float
    key_actions: List[str]
    success: bool
    error: Optional[str] = None


class AgentSummaryService:
    """
    Generates and stores summaries of agent activity.
    """

    def __init__(self):
        self._summaries: Dict[str, AgentSummary] = {}

    async def create_summary(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        token_usage: int,
        duration: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> AgentSummary:
        """Create a summary for a session"""
        turn_count = sum(1 for m in messages if m.get("role") == "user")
        tool_count = len(tool_results)

        # Extract key actions
        key_actions = []
        for result in tool_results[:5]:  # First 5 tool results
            tool_name = result.get("name", "unknown")
            key_actions.append(f"Used {tool_name}")

        summary = AgentSummary(
            session_id=session_id,
            turn_count=turn_count,
            tool_count=tool_count,
            token_usage=token_usage,
            duration=duration,
            key_actions=key_actions,
            success=success,
            error=error
        )

        self._summaries[session_id] = summary
        return summary

    def get_summary(self, session_id: str) -> Optional[AgentSummary]:
        """Get a summary by session ID"""
        return self._summaries.get(session_id)

    def list_summaries(self, limit: int = 10) -> List[AgentSummary]:
        """List recent summaries"""
        summaries = list(self._summaries.values())
        summaries.sort(key=lambda s: s.session_id, reverse=True)
        return summaries[:limit]


# Global summary service
_summary_service: Optional[AgentSummaryService] = None


def get_summary_service() -> AgentSummaryService:
    """Get the global summary service"""
    global _summary_service
    if _summary_service is None:
        _summary_service = AgentSummaryService()
    return _summary_service