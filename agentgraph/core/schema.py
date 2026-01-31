"""
AgentGraph Core Schema

Defines the data models for tracking agent activities and building the memory graph.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class EventType(str, Enum):
    """Types of agent events."""
    # Actions
    ACTION_START = "action.start"
    ACTION_COMPLETE = "action.complete"
    ACTION_ERROR = "action.error"
    
    # Tool Usage
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    
    # Decisions
    DECISION = "decision"
    REASONING = "reasoning"
    
    # Communication
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    
    # Memory
    MEMORY_STORE = "memory.store"
    MEMORY_RETRIEVE = "memory.retrieve"
    
    # State
    STATE_CHANGE = "state.change"
    
    # Custom
    CUSTOM = "custom"


class EntityType(str, Enum):
    """Types of entities in the graph."""
    AGENT = "agent"
    USER = "user"
    TASK = "task"
    RESOURCE = "resource"
    DOCUMENT = "document"
    MESSAGE = "message"
    TOOL = "tool"
    SESSION = "session"
    CUSTOM = "custom"


class RelationType(str, Enum):
    """Types of relationships between entities."""
    CREATED = "created"
    MODIFIED = "modified"
    REFERENCED = "referenced"
    DEPENDS_ON = "depends_on"
    CAUSED = "caused"
    RESPONDED_TO = "responded_to"
    PART_OF = "part_of"
    OWNS = "owns"
    DELEGATED_TO = "delegated_to"
    COLLABORATED_WITH = "collaborated_with"


@dataclass
class Entity:
    """
    An entity in the agent graph.
    
    Entities are the "nouns" - agents, users, tasks, documents, etc.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    type: EntityType = EntityType.CUSTOM
    name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            id=data["id"],
            type=EntityType(data["type"]),
            name=data.get("name", ""),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class Event:
    """
    An event in the agent activity stream.
    
    Events are the "verbs" - actions, decisions, communications, etc.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    type: EventType = EventType.CUSTOM
    
    # Who
    agent_id: str = ""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # What
    action: str = ""
    description: str = ""
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    
    # Context
    parent_event_id: Optional[str] = None
    related_entity_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Outcome
    status: str = "success"  # success, error, pending
    error_message: Optional[str] = None
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "action": self.action,
            "description": self.description,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "parent_event_id": self.parent_event_id,
            "related_entity_ids": self.related_entity_ids,
            "tags": self.tags,
            "metadata": self.metadata,
            "status": self.status,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=data["id"],
            type=EventType(data["type"]),
            agent_id=data.get("agent_id", ""),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            action=data.get("action", ""),
            description=data.get("description", ""),
            input_data=data.get("input_data"),
            output_data=data.get("output_data"),
            parent_event_id=data.get("parent_event_id"),
            related_entity_ids=data.get("related_entity_ids", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            status=data.get("status", "success"),
            error_message=data.get("error_message"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            duration_ms=data.get("duration_ms")
        )


@dataclass
class Relationship:
    """
    A relationship between entities in the graph.
    
    Relationships connect entities and can be created by events.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    type: RelationType = RelationType.REFERENCED
    
    # From -> To
    source_entity_id: str = ""
    target_entity_id: str = ""
    
    # Context
    created_by_event_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "created_by_event_id": self.created_by_event_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        return cls(
            id=data["id"],
            type=RelationType(data["type"]),
            source_entity_id=data["source_entity_id"],
            target_entity_id=data["target_entity_id"],
            created_by_event_id=data.get("created_by_event_id"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            valid_until=datetime.fromisoformat(data["valid_until"]) if data.get("valid_until") else None
        )


@dataclass
class Agent:
    """
    An AI agent registered in the system.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    platform: str = ""  # openai, langchain, crewai, openclaw, custom
    owner_id: Optional[str] = None
    api_key: str = field(default_factory=lambda: str(uuid4()))
    
    # Config
    config: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    
    # Status
    is_active: bool = True
    last_seen: Optional[datetime] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "owner_id": self.owner_id,
            "config": self.config,
            "capabilities": self.capabilities,
            "is_active": self.is_active,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat()
        }


@dataclass  
class Session:
    """
    A session/conversation context for an agent.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    user_id: Optional[str] = None
    
    # Context
    name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    is_active: bool = True
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "name": self.name,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None
        }
