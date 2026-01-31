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

# Import integrations (optional dependencies)
try:
    from .integrations.openai_assistants import (
        OpenAIAssistantsTracker,
        AssistantEventHandler,
        track_assistant_run
    )
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False
    OpenAIAssistantsTracker = None
    AssistantEventHandler = None
    track_assistant_run = None

__version__ = "0.2.0"
__all__ = [
    # Core schema
    "Agent",
    "Entity",
    "EntityType", 
    "Event",
    "EventType",
    "Relationship",
    "RelationType",
    "Session",
    # SDK
    "AgentGraphClient",
    "LangChainCallback",
    # Integrations (when available)
    "OpenAIAssistantsTracker",
    "AssistantEventHandler",
    "track_assistant_run",
]
