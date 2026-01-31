"""
Sharing Hub

The central coordinator for cross-agent context sharing.
Manages connections, subscriptions, and event routing.
"""

from datetime import datetime
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .protocol import ContextProtocol, ContextEvent, Topic


@dataclass
class ConnectedAgent:
    """Represents a connected agent."""
    agent_id: str
    name: str = ""
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    
    # Async callback for sending events
    send_callback: Optional[Callable] = None
    
    # Stats
    events_sent: int = 0
    events_received: int = 0


class SharingHub:
    """
    Central hub for cross-agent context sharing.
    
    Features:
    - Real-time event routing between agents
    - Subscription management
    - Conflict detection
    - Event history for late joiners
    
    Usage:
        hub = SharingHub()
        
        # Agent connects
        hub.connect_agent("agent-1", "ResearchAgent")
        
        # Subscribe to events
        hub.subscribe("agent-1", topics={Topic.DECISION_MADE})
        
        # Publish an event
        hub.publish(ContextEvent(
            source_agent_id="agent-1",
            topic=Topic.DECISION_MADE,
            action="chose_strategy",
            description="Decided to use approach A"
        ))
    """
    
    def __init__(self, history_size: int = 1000):
        self.protocol = ContextProtocol()
        self.connected_agents: Dict[str, ConnectedAgent] = {}
        self.event_history: List[ContextEvent] = []
        self.history_size = history_size
        
        # Conflict detection
        self.entity_locks: Dict[str, str] = {}  # entity_id -> agent_id working on it
        self.conflict_callbacks: List[Callable] = []
    
    # ==================== Connection Management ====================
    
    def connect_agent(
        self,
        agent_id: str,
        name: str = "",
        send_callback: Optional[Callable] = None
    ) -> ConnectedAgent:
        """
        Register an agent as connected to the hub.
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable name
            send_callback: Async function to send events to this agent
        """
        agent = ConnectedAgent(
            agent_id=agent_id,
            name=name or agent_id,
            send_callback=send_callback
        )
        self.connected_agents[agent_id] = agent
        
        # Broadcast connection event
        self._broadcast_system_event(
            f"Agent '{name or agent_id}' connected",
            {"agent_id": agent_id, "action": "connected"}
        )
        
        return agent
    
    def disconnect_agent(self, agent_id: str):
        """Disconnect an agent from the hub."""
        if agent_id in self.connected_agents:
            agent = self.connected_agents.pop(agent_id)
            
            # Remove all subscriptions
            if agent_id in self.protocol.agent_subscriptions:
                sub_ids = list(self.protocol.agent_subscriptions[agent_id])
                for sub_id in sub_ids:
                    self.protocol.unsubscribe(sub_id)
            
            # Release any entity locks
            locked_entities = [eid for eid, aid in self.entity_locks.items() if aid == agent_id]
            for entity_id in locked_entities:
                del self.entity_locks[entity_id]
            
            # Broadcast disconnection
            self._broadcast_system_event(
                f"Agent '{agent.name}' disconnected",
                {"agent_id": agent_id, "action": "disconnected"}
            )
    
    def get_connected_agents(self) -> List[Dict]:
        """Get list of connected agents."""
        return [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "connected_at": a.connected_at.isoformat(),
                "events_sent": a.events_sent,
                "events_received": a.events_received
            }
            for a in self.connected_agents.values()
        ]
    
    # ==================== Subscription Management ====================
    
    def subscribe(
        self,
        agent_id: str,
        topics: Optional[Set[Topic]] = None,
        entity_ids: Optional[Set[str]] = None,
        source_agent_ids: Optional[Set[str]] = None,
        **kwargs
    ) -> str:
        """Create a subscription for an agent."""
        return self.protocol.subscribe(
            agent_id=agent_id,
            topics=topics,
            entity_ids=entity_ids,
            source_agent_ids=source_agent_ids,
            **kwargs
        )
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        return self.protocol.unsubscribe(subscription_id)
    
    # ==================== Event Publishing ====================
    
    async def publish(self, event: ContextEvent) -> List[str]:
        """
        Publish an event to subscribed agents.
        
        Returns:
            List of agent IDs that received the event
        """
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.history_size:
            self.event_history = self.event_history[-self.history_size:]
        
        # Update sender stats
        if event.source_agent_id in self.connected_agents:
            self.connected_agents[event.source_agent_id].events_sent += 1
        
        # Check for conflicts
        if event.entity_id:
            conflict = self._check_conflict(event)
            if conflict:
                await self._handle_conflict(event, conflict)
        
        # Route to subscribers
        recipients = self.protocol.route_event(event)
        
        # Send to connected agents
        for agent_id in recipients:
            if agent_id in self.connected_agents:
                agent = self.connected_agents[agent_id]
                agent.events_received += 1
                agent.last_seen = datetime.utcnow()
                
                if agent.send_callback:
                    try:
                        await agent.send_callback(event.to_dict())
                    except Exception as e:
                        print(f"Error sending to agent {agent_id}: {e}")
        
        return recipients
    
    def publish_sync(self, event: ContextEvent) -> List[str]:
        """Synchronous version of publish."""
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.history_size:
            self.event_history = self.event_history[-self.history_size:]
        
        # Update sender stats
        if event.source_agent_id in self.connected_agents:
            self.connected_agents[event.source_agent_id].events_sent += 1
        
        # Route to subscribers (without async callbacks)
        return self.protocol.route_event(event)
    
    # ==================== Conflict Detection ====================
    
    def claim_entity(self, agent_id: str, entity_id: str) -> bool:
        """
        Claim exclusive work on an entity.
        
        Returns:
            True if claim successful, False if already claimed
        """
        if entity_id in self.entity_locks:
            return self.entity_locks[entity_id] == agent_id
        
        self.entity_locks[entity_id] = agent_id
        return True
    
    def release_entity(self, agent_id: str, entity_id: str) -> bool:
        """Release a claim on an entity."""
        if entity_id in self.entity_locks and self.entity_locks[entity_id] == agent_id:
            del self.entity_locks[entity_id]
            return True
        return False
    
    def _check_conflict(self, event: ContextEvent) -> Optional[str]:
        """Check if an event conflicts with existing work."""
        if not event.entity_id:
            return None
        
        current_owner = self.entity_locks.get(event.entity_id)
        if current_owner and current_owner != event.source_agent_id:
            return current_owner
        
        return None
    
    async def _handle_conflict(self, event: ContextEvent, conflicting_agent_id: str):
        """Handle a detected conflict."""
        conflict_event = ContextEvent(
            topic=Topic.CONFLICT,
            source_agent_id="system",
            target_agent_ids=[event.source_agent_id, conflicting_agent_id],
            event_type="conflict.detected",
            action="entity_conflict",
            description=f"Conflict on entity {event.entity_id}",
            entity_id=event.entity_id,
            data={
                "original_owner": conflicting_agent_id,
                "conflicting_agent": event.source_agent_id,
                "conflicting_event": event.to_dict()
            },
            priority=10,  # High priority
            requires_ack=True
        )
        
        await self.publish(conflict_event)
        
        # Call registered conflict callbacks
        for callback in self.conflict_callbacks:
            try:
                callback(event, conflicting_agent_id)
            except Exception as e:
                print(f"Error in conflict callback: {e}")
    
    def on_conflict(self, callback: Callable):
        """Register a callback for conflict detection."""
        self.conflict_callbacks.append(callback)
    
    # ==================== Querying ====================
    
    def get_recent_events(
        self,
        agent_id: Optional[str] = None,
        topic: Optional[Topic] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ContextEvent]:
        """Get recent events from history."""
        events = self.event_history
        
        if agent_id:
            events = [e for e in events if e.source_agent_id == agent_id]
        
        if topic:
            events = [e for e in events if e.topic == topic]
        
        if entity_id:
            events = [e for e in events if e.entity_id == entity_id]
        
        return events[-limit:]
    
    def query_agents(self, question: str) -> Dict:
        """
        Query across all agents' shared context.
        
        Simple keyword matching for now - could integrate with semantic search.
        """
        question_lower = question.lower()
        matching_events = []
        
        for event in self.event_history:
            text = f"{event.action} {event.description} {event.event_type}".lower()
            if any(word in text for word in question_lower.split()):
                matching_events.append(event)
        
        return {
            "question": question,
            "events": [e.to_dict() for e in matching_events[-20:]],
            "count": len(matching_events)
        }
    
    # ==================== Helpers ====================
    
    def _broadcast_system_event(self, description: str, data: Dict):
        """Broadcast a system event to all agents."""
        event = ContextEvent(
            source_agent_id="system",
            topic=Topic.ALL,
            event_type="system",
            description=description,
            data=data
        )
        self.publish_sync(event)


# Global hub instance
_sharing_hub: Optional[SharingHub] = None


def get_sharing_hub() -> SharingHub:
    """Get or create the global sharing hub."""
    global _sharing_hub
    if _sharing_hub is None:
        _sharing_hub = SharingHub()
    return _sharing_hub
