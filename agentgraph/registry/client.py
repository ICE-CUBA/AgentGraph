"""
High-level client API for Agent Registry.

Provides simple functions for common registry operations,
similar to the easy.py pattern for event logging.
"""

import uuid
from typing import Optional, List, Union

from .models import Agent, AgentStatus, Capability
from .registry import AgentRegistry

# Global registry instance (lazy init)
_registry: Optional[AgentRegistry] = None


def _get_registry() -> AgentRegistry:
    """Get or create the global registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def register_agent(
    name: str,
    capabilities: Optional[List[Union[str, dict, Capability]]] = None,
    description: str = "",
    endpoint: Optional[str] = None,
    agent_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Agent:
    """
    Register an agent with the registry.
    
    Args:
        name: Human-readable agent name
        capabilities: List of capabilities (strings, dicts, or Capability objects)
        description: What this agent does
        endpoint: How to reach this agent (URL, queue name, etc.)
        agent_id: Unique ID (auto-generated if not provided)
        metadata: Additional agent metadata
        
    Returns:
        The registered Agent
        
    Example:
        >>> agent = register_agent(
        ...     name="TranslatorBot",
        ...     capabilities=["translate", {"name": "summarize", "metadata": {"max_length": 1000}}],
        ...     description="Translates and summarizes text"
        ... )
    """
    registry = _get_registry()
    
    # Normalize capabilities
    caps = []
    for cap in (capabilities or []):
        if isinstance(cap, str):
            caps.append(Capability(name=cap))
        elif isinstance(cap, dict):
            caps.append(Capability.from_dict(cap))
        elif isinstance(cap, Capability):
            caps.append(cap)
    
    agent = Agent(
        id=agent_id or str(uuid.uuid4()),
        name=name,
        description=description,
        capabilities=caps,
        endpoint=endpoint,
        metadata=metadata or {},
    )
    
    return registry.register(agent)


def unregister_agent(agent_id: str) -> bool:
    """
    Remove an agent from the registry.
    
    Args:
        agent_id: ID of agent to remove
        
    Returns:
        True if removed, False if not found
    """
    return _get_registry().unregister(agent_id)


def discover_agents(
    capability: Optional[str] = None,
    online_only: bool = True,
    **filters
) -> List[Agent]:
    """
    Find agents matching criteria.
    
    Args:
        capability: Required capability name
        online_only: Only return online agents (default True)
        **filters: Additional capability metadata filters
        
    Returns:
        List of matching agents
        
    Example:
        >>> # Find any online translator
        >>> translators = discover_agents("translate")
        
        >>> # Find translators that speak French
        >>> french = discover_agents("translate", languages="fr")
    """
    return _get_registry().discover(
        capability=capability,
        online_only=online_only,
        **filters
    )


def get_agent(agent_id: str) -> Optional[Agent]:
    """
    Get a specific agent by ID.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        Agent if found, None otherwise
    """
    return _get_registry().get(agent_id)


def update_status(agent_id: str, status: str | AgentStatus) -> bool:
    """
    Update an agent's status.
    
    Args:
        agent_id: Agent ID
        status: New status ("online", "busy", "offline")
        
    Returns:
        True if updated, False if agent not found
    """
    if isinstance(status, str):
        status = AgentStatus(status)
    return _get_registry().update_status(agent_id, status)


def heartbeat(agent_id: str) -> bool:
    """
    Send a heartbeat for an agent.
    
    Should be called periodically to indicate agent is still alive.
    Agents that don't heartbeat within 5 minutes are marked offline.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        True if successful, False if agent not found
    """
    return _get_registry().heartbeat(agent_id)


def list_agents(online_only: bool = False) -> List[Agent]:
    """
    List all registered agents.
    
    Args:
        online_only: Only return online agents
        
    Returns:
        List of all agents
    """
    if online_only:
        return _get_registry().discover(online_only=True)
    return _get_registry().list_all()


def agent_count(online_only: bool = False) -> int:
    """
    Count registered agents.
    
    Args:
        online_only: Only count online agents
        
    Returns:
        Number of agents
    """
    return _get_registry().count(online_only=online_only)
