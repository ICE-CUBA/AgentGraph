"""
Agent Registry - Discovery and coordination for multi-agent systems.

Enables agents to:
- Register themselves with capabilities
- Discover other agents by capability
- Track online/offline status
- Broadcast presence updates
- Build trust through successful task completion
"""

from .models import Agent, Capability, AgentStatus
from .registry import AgentRegistry
from .client import (
    register_agent,
    unregister_agent,
    discover_agents,
    get_agent,
    update_status,
    heartbeat,
)
from .reputation import (
    ReputationTracker,
    TaskOutcome,
    record_task,
    complete_task,
    rate_agent,
    get_trust,
    get_reputation_tracker,
)

__all__ = [
    # Core registry
    "Agent",
    "Capability",
    "AgentStatus",
    "AgentRegistry",
    "register_agent",
    "unregister_agent",
    "discover_agents",
    "get_agent",
    "update_status",
    "heartbeat",
    # Reputation system
    "ReputationTracker",
    "TaskOutcome",
    "record_task",
    "complete_task",
    "rate_agent",
    "get_trust",
    "get_reputation_tracker",
]
