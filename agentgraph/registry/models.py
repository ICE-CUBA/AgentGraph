"""
Data models for Agent Registry.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AgentStatus(str, Enum):
    """Agent availability status."""
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class Capability:
    """
    A capability that an agent can provide.
    
    Examples:
        - Capability("translate", {"languages": ["en", "es", "fr"]})
        - Capability("code_review", {"languages": ["python", "typescript"]})
        - Capability("web_search")
    """
    name: str
    metadata: dict = field(default_factory=dict)
    
    def matches(self, query: str, **kwargs) -> bool:
        """Check if this capability matches a query."""
        if query.lower() != self.name.lower():
            return False
        
        # Check metadata filters (strict: key must exist if filtered)
        for key, value in kwargs.items():
            if key not in self.metadata:
                # If filtering by a key, capability must have it
                return False
            cap_value = self.metadata[key]
            if isinstance(cap_value, list):
                if value not in cap_value:
                    return False
            elif cap_value != value:
                return False
        
        return True
    
    def to_dict(self) -> dict:
        return {"name": self.name, "metadata": self.metadata}
    
    @classmethod
    def from_dict(cls, data: dict) -> "Capability":
        return cls(name=data["name"], metadata=data.get("metadata", {}))


@dataclass
class Agent:
    """
    A registered agent in the network.
    
    Agents advertise their capabilities and can be discovered
    by other agents needing those capabilities.
    """
    id: str
    name: str
    description: str = ""
    capabilities: list[Capability] = field(default_factory=list)
    status: AgentStatus = AgentStatus.UNKNOWN
    endpoint: Optional[str] = None  # How to reach this agent
    metadata: dict = field(default_factory=dict)
    
    # Timestamps
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    
    # Trust (future: reputation system)
    trust_score: float = 0.5  # 0.0 to 1.0
    
    def has_capability(self, name: str, **kwargs) -> bool:
        """Check if agent has a specific capability."""
        return any(cap.matches(name, **kwargs) for cap in self.capabilities)
    
    def is_online(self) -> bool:
        """Check if agent is currently online."""
        return self.status in (AgentStatus.ONLINE, AgentStatus.BUSY)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "status": self.status.value,
            "endpoint": self.endpoint,
            "metadata": self.metadata,
            "registered_at": self.registered_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "trust_score": self.trust_score,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            capabilities=[Capability.from_dict(c) for c in data.get("capabilities", [])],
            status=AgentStatus(data.get("status", "unknown")),
            endpoint=data.get("endpoint"),
            metadata=data.get("metadata", {}),
            registered_at=datetime.fromisoformat(data["registered_at"]) if "registered_at" in data else datetime.utcnow(),
            last_seen=datetime.fromisoformat(data["last_seen"]) if "last_seen" in data else datetime.utcnow(),
            trust_score=data.get("trust_score", 0.5),
        )
