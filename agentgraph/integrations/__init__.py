"""
AgentGraph Integrations

Pre-built integrations for popular agent frameworks.
"""

# OpenAI Assistants
try:
    from .openai_assistants import (
        OpenAIAssistantsTracker,
        AssistantEventHandler,
        track_assistant_run
    )
except ImportError:
    OpenAIAssistantsTracker = None
    AssistantEventHandler = None
    track_assistant_run = None

# CrewAI
try:
    from .crewai import CrewAITracker, CrewAICallback
except ImportError:
    CrewAITracker = None
    CrewAICallback = None

__all__ = [
    "OpenAIAssistantsTracker",
    "AssistantEventHandler",
    "track_assistant_run",
    "CrewAITracker",
    "CrewAICallback"
]
