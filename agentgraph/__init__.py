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
except ImportError:
    OpenAIAssistantsTracker = None
    AssistantEventHandler = None
    track_assistant_run = None

try:
    from .integrations.crewai import CrewAITracker, CrewAICallback
except ImportError:
    CrewAITracker = None
    CrewAICallback = None

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
    "CrewAITracker",
    "CrewAICallback",
]
