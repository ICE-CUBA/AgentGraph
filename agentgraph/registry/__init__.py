"""
Agent Registry - Discovery and coordination for multi-agent systems.

Enables agents to:
- Register themselves with capabilities
- Discover other agents by capability
- Track online/offline status
- Broadcast presence updates
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

__all__ = [
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
]
