"""
Agents Module - DEPRECATED

================================================================================
DEPRECATED: Multi-agent system has been disabled
================================================================================

Single-agent direct execution mode is now used via MainAgent.
All other agent classes (PMAgent, ResearchAgent, etc.) are deprecated.

- OLD: get_agent(role) → specific agent instance
- NEW: MainAgent.think() → single agent handles everything

================================================================================
"""

# MainAgent is the only supported agent now
from app.agents.main_agent import MainAgent

__all__ = ["MainAgent"]