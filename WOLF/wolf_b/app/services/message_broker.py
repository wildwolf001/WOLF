"""
Message Broker - Agent-to-Agent communication

================================================================================
DEPRECATED - Multi-agent messaging disabled
================================================================================

Single-agent direct execution mode no longer uses message broker.
All communication now happens through MainAgent.think().

For future multi-agent extension, use a proper message queue (Redis, etc.)
================================================================================
"""
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass

# Import AgentMessage from base for compatibility
try:
    from app.agents.base import AgentMessage
except ImportError:
    # Fallback if base.py is also deprecated
    @dataclass
    class AgentMessage:
        id: str
        from_role: str
        to_role: str
        type: str
        content: str
        timestamp: datetime
        task_id: Optional[str] = None
        session_id: Optional[str] = None
        metadata: Optional[Dict[str, Any]] = None


class MessageBroker:
    """
    Manages message passing between agents.
    DEPRECATED - Single-agent mode does not use message broker.
    """

    def __init__(self):
        self._messages: List[AgentMessage] = []
        self._subscriptions: Dict[str, List[str]] = {}

    async def send_message(
        self,
        from_role: str,
        to_role: str,
        content: str,
        msg_type: str = "result",
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Send a message - DEPRECATED, raises error"""
        raise RuntimeError(
            "MessageBroker is deprecated. "
            "Use single-agent MainAgent.think() instead."
        )

    async def broadcast(
        self,
        from_role: str,
        content: str,
        msg_type: str = "broadcast",
        task_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AgentMessage:
        """Broadcast - DEPRECATED"""
        raise RuntimeError(
            "MessageBroker is deprecated. "
            "Use single-agent MainAgent.think() instead."
        )

    def get_messages_for_agent(
        self,
        agent_role: str,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> List[AgentMessage]:
        """Get messages - returns empty list in single-agent mode"""
        return []

    def get_conversation(
        self,
        session_id: str,
        task_id: Optional[str] = None
    ) -> List[AgentMessage]:
        """Get conversation - returns empty list"""
        return []

    async def delegate_task(
        self,
        from_role: str,
        to_role: str,
        task: Dict[str, Any],
        session_id: str
    ) -> AgentMessage:
        """Delegate task - DEPRECATED"""
        raise RuntimeError(
            "MessageBroker.delegate_task is deprecated. "
            "Use single-agent MainAgent.think() instead."
        )

    async def report_result(
        self,
        from_role: str,
        to_role: str,
        result: str,
        task_id: str,
        session_id: str
    ) -> AgentMessage:
        """Report result - DEPRECATED"""
        raise RuntimeError(
            "MessageBroker.report_result is deprecated. "
            "Use single-agent MainAgent.think() instead."
        )

    async def ask_question(
        self,
        from_role: str,
        to_role: str,
        question: str,
        task_id: str,
        session_id: str
    ) -> AgentMessage:
        """Ask question - DEPRECATED"""
        raise RuntimeError(
            "MessageBroker.ask_question is deprecated. "
            "Use single-agent MainAgent.think() instead."
        )


# Singleton instance - preserved for compatibility
message_broker = MessageBroker()