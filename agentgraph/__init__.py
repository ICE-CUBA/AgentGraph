"""
AgentGraph - Infrastructure for Multi-Agent AI Systems

The simplest way to get started:

    from agentgraph import log, query
    
    log("searched for papers")
    results = query("what did I do?")

That's it. No server setup, no API keys, no config.
Server starts automatically when needed.

For more control, use the full SDK:

    from agentgraph import AgentGraphClient
    client = AgentGraphClient(api_key="...")
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

# Easy mode - zero config, just works
from .easy import (
    log,
    query,
    search,
    connect,
    share,
    entity,
    link,
    track
)

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
    # Easy mode (recommended for getting started)
    "log",
    "query", 
    "search",
    "connect",
    "share",
    "entity",
    "link",
    "track",
    # Core schema
    "Agent",
    "Entity",
    "EntityType", 
    "Event",
    "EventType",
    "Relationship",
    "RelationType",
    "Session",
    # Full SDK (for more control)
    "AgentGraphClient",
    "LangChainCallback",
    # Integrations (when available)
    "OpenAIAssistantsTracker",
    "AssistantEventHandler",
    "track_assistant_run",
    "CrewAITracker",
    "CrewAICallback",
]
