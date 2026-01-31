"""
Context Sharing Protocol

Defines the standard for agents to publish and subscribe to context.

Key concepts:
- ContextEvent: A piece of context being shared
- Subscription: An agent's interest in certain events
- Topics: Categories of events (entity changes, decisions, etc.)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional, Set
from uuid import uuid4


class Topic(str, Enum):
    """Topics agents can subscribe to."""
    # Entity changes
    ENTITY_CREATED = "entity.created"
    ENTITY_MODIFIED = "entity.modified"
    ENTITY_DELETED = "entity.deleted"
    
    # Agent actions
    ACTION_STARTED = "action.started"
    ACTION_COMPLETED = "action.completed"
    ACTION_FAILED = "action.failed"
    
    # Decisions
    DECISION_MADE = "decision.made"
    
    # Tool usage
    TOOL_CALLED = "tool.called"
    TOOL_RESULT = "tool.result"
    
    # Collaboration
    HELP_REQUESTED = "help.requested"
    HANDOFF = "handoff"
    CONFLICT = "conflict.detected"
    
    # Catch-all
    ALL = "*"


@dataclass
class ContextEvent:
    """
    A context event that can be shared between agents.
    
    This is the unit of context sharing - when an agent does something
    notable, it publishes a ContextEvent for other agents to see.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    topic: Topic = Topic.ALL
    
    # Who
    source_agent_id: str = ""
    target_agent_ids: List[str] = field(default_factory=list)  # Empty = broadcast
    
    # What
    event_type: str = ""
    action: str = ""
    description: str = ""
    
    # Context
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    data: Dict = field(default_factory=dict)
    
    # When
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # For time-sensitive context
    
    # Priority
    priority: int = 0  # Higher = more important
    requires_ack: bool = False  # Whether receiver must acknowledge
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "topic": self.topic.value,
            "source_agent_id": self.source_agent_id,
            "target_agent_ids": self.target_agent_ids,
            "event_type": self.event_type,
            "action": self.action,
            "description": self.description,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "priority": self.priority,
            "requires_ack": self.requires_ack
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ContextEvent":
        return cls(
            id=data.get("id", str(uuid4())),
            topic=Topic(data.get("topic", "*")),
            source_agent_id=data.get("source_agent_id", ""),
            target_agent_ids=data.get("target_agent_ids", []),
            event_type=data.get("event_type", ""),
            action=data.get("action", ""),
            description=data.get("description", ""),
            entity_id=data.get("entity_id"),
            entity_type=data.get("entity_type"),
            data=data.get("data", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            priority=data.get("priority", 0),
            requires_ack=data.get("requires_ack", False)
        )


@dataclass
class Subscription:
    """
    An agent's subscription to context events.
    
    Defines what events an agent wants to receive.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    
    # What to subscribe to
    topics: Set[Topic] = field(default_factory=lambda: {Topic.ALL})
    entity_ids: Set[str] = field(default_factory=set)  # Specific entities to watch
    entity_types: Set[str] = field(default_factory=set)  # Types of entities
    source_agent_ids: Set[str] = field(default_factory=set)  # Specific agents to watch
    
    # Filters
    min_priority: int = 0
    
    # Callback for when matching events arrive
    callback: Optional[Callable[[ContextEvent], None]] = None
    
    # Active status
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def matches(self, event: ContextEvent) -> bool:
        """Check if an event matches this subscription."""
        if not self.is_active:
            return False
        
        # Priority filter
        if event.priority < self.min_priority:
            return False
        
        # Topic filter
        if Topic.ALL not in self.topics and event.topic not in self.topics:
            return False
        
        # Entity filter
        if self.entity_ids and event.entity_id not in self.entity_ids:
            return False
        
        if self.entity_types and event.entity_type not in self.entity_types:
            return False
        
        # Source agent filter
        if self.source_agent_ids and event.source_agent_id not in self.source_agent_ids:
            return False
        
        # Target filter - if event has specific targets, we must be one of them
        if event.target_agent_ids and self.agent_id not in event.target_agent_ids:
            return False
        
        return True


class ContextProtocol:
    """
    The context sharing protocol.
    
    Manages subscriptions and event routing between agents.
    """
    
    def __init__(self):
        self.subscriptions: Dict[str, Subscription] = {}  # sub_id -> subscription
        self.agent_subscriptions: Dict[str, Set[str]] = {}  # agent_id -> set of sub_ids
        self.pending_acks: Dict[str, ContextEvent] = {}  # event_id -> event requiring ack
    
    def subscribe(
        self,
        agent_id: str,
        topics: Optional[Set[Topic]] = None,
        entity_ids: Optional[Set[str]] = None,
        entity_types: Optional[Set[str]] = None,
        source_agent_ids: Optional[Set[str]] = None,
        min_priority: int = 0,
        callback: Optional[Callable[[ContextEvent], None]] = None
    ) -> str:
        """
        Create a subscription for an agent.
        
        Returns:
            Subscription ID
        """
        sub = Subscription(
            agent_id=agent_id,
            topics=topics or {Topic.ALL},
            entity_ids=entity_ids or set(),
            entity_types=entity_types or set(),
            source_agent_ids=source_agent_ids or set(),
            min_priority=min_priority,
            callback=callback
        )
        
        self.subscriptions[sub.id] = sub
        
        if agent_id not in self.agent_subscriptions:
            self.agent_subscriptions[agent_id] = set()
        self.agent_subscriptions[agent_id].add(sub.id)
        
        return sub.id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        if subscription_id not in self.subscriptions:
            return False
        
        sub = self.subscriptions.pop(subscription_id)
        if sub.agent_id in self.agent_subscriptions:
            self.agent_subscriptions[sub.agent_id].discard(subscription_id)
        
        return True
    
    def get_matching_subscriptions(self, event: ContextEvent) -> List[Subscription]:
        """Get all subscriptions that match an event."""
        return [sub for sub in self.subscriptions.values() if sub.matches(event)]
    
    def route_event(self, event: ContextEvent) -> List[str]:
        """
        Route an event to matching subscribers.
        
        Returns:
            List of agent IDs that received the event
        """
        recipients = []
        matching_subs = self.get_matching_subscriptions(event)
        
        for sub in matching_subs:
            recipients.append(sub.agent_id)
            
            # Call callback if registered
            if sub.callback:
                try:
                    sub.callback(event)
                except Exception as e:
                    print(f"Error in subscription callback: {e}")
        
        # Track events requiring acknowledgment
        if event.requires_ack:
            self.pending_acks[event.id] = event
        
        return list(set(recipients))  # Dedupe
    
    def acknowledge(self, event_id: str, agent_id: str) -> bool:
        """Acknowledge receipt of an event."""
        if event_id in self.pending_acks:
            # Could track which agents have acked
            return True
        return False
