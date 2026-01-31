"""
AgentGraph - Memory Layer for AI Agents

Track, visualize, and share context between AI agents.
"""

from .core.schema import (
    Agent,
    Entity,
    EntityType,
    Event,
    EventType,
    Relationship,
    RelationType,
    Session
)

from .sdk.client import AgentGraphClient, LangChainCallback

__version__ = "0.1.0"
__all__ = [
    "Agent",
    "Entity",
    "EntityType", 
    "Event",
    "EventType",
    "Relationship",
    "RelationType",
    "Session",
    "AgentGraphClient",
    "LangChainCallback"
]
