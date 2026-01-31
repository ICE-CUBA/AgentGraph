"""
Tests for Cross-Agent Sharing
"""

import pytest
from fastapi.testclient import TestClient

from agentgraph.api.server import app
from agentgraph.sharing.protocol import ContextEvent, Topic, Subscription, ContextProtocol
from agentgraph.sharing.hub import SharingHub


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def api_key(client):
    """Create an agent and return its API key."""
    response = client.post("/agents", json={
        "name": "SharingTestAgent",
        "platform": "test"
    })
    return response.json()["api_key"]


@pytest.fixture
def api_key_2(client):
    """Create a second agent."""
    response = client.post("/agents", json={
        "name": "SharingTestAgent2",
        "platform": "test"
    })
    return response.json()["api_key"]


class TestContextProtocol:
    """Tests for the context protocol."""

    def test_context_event_creation(self):
        """Test creating a context event."""
        event = ContextEvent(
            source_agent_id="agent-1",
            topic=Topic.DECISION_MADE,
            action="chose_strategy",
            description="Decided to use approach A"
        )
        
        assert event.source_agent_id == "agent-1"
        assert event.topic == Topic.DECISION_MADE
        assert event.action == "chose_strategy"

    def test_context_event_serialization(self):
        """Test event to_dict and from_dict."""
        event = ContextEvent(
            source_agent_id="agent-1",
            topic=Topic.ACTION_COMPLETED,
            action="task_done",
            entity_id="entity-123"
        )
        
        data = event.to_dict()
        restored = ContextEvent.from_dict(data)
        
        assert restored.source_agent_id == event.source_agent_id
        assert restored.topic == event.topic
        assert restored.entity_id == event.entity_id

    def test_subscription_matching(self):
        """Test subscription matching logic."""
        sub = Subscription(
            agent_id="agent-1",
            topics={Topic.DECISION_MADE, Topic.ACTION_COMPLETED}
        )
        
        # Should match
        event1 = ContextEvent(topic=Topic.DECISION_MADE, source_agent_id="agent-2")
        assert sub.matches(event1)
        
        # Should not match (wrong topic)
        event2 = ContextEvent(topic=Topic.TOOL_CALLED, source_agent_id="agent-2")
        assert not sub.matches(event2)

    def test_subscription_entity_filter(self):
        """Test subscription with entity filter."""
        sub = Subscription(
            agent_id="agent-1",
            entity_ids={"entity-123"}
        )
        
        # Should match
        event1 = ContextEvent(entity_id="entity-123", source_agent_id="agent-2")
        assert sub.matches(event1)
        
        # Should not match (wrong entity)
        event2 = ContextEvent(entity_id="entity-456", source_agent_id="agent-2")
        assert not sub.matches(event2)

    def test_protocol_subscribe_unsubscribe(self):
        """Test protocol subscription management."""
        protocol = ContextProtocol()
        
        sub_id = protocol.subscribe(
            agent_id="agent-1",
            topics={Topic.ALL}
        )
        
        assert sub_id in protocol.subscriptions
        assert "agent-1" in protocol.agent_subscriptions
        
        protocol.unsubscribe(sub_id)
        assert sub_id not in protocol.subscriptions


class TestSharingHub:
    """Tests for the sharing hub."""

    def test_connect_disconnect(self):
        """Test agent connection management."""
        hub = SharingHub()
        
        hub.connect_agent("agent-1", "TestAgent")
        assert "agent-1" in hub.connected_agents
        
        hub.disconnect_agent("agent-1")
        assert "agent-1" not in hub.connected_agents

    def test_publish_sync(self):
        """Test synchronous event publishing."""
        hub = SharingHub()
        
        hub.connect_agent("agent-1", "Agent1")
        hub.connect_agent("agent-2", "Agent2")
        
        # Agent 2 subscribes
        hub.subscribe("agent-2", topics={Topic.ALL})
        
        # Agent 1 publishes
        event = ContextEvent(
            source_agent_id="agent-1",
            topic=Topic.ACTION_COMPLETED,
            action="test_action"
        )
        
        recipients = hub.publish_sync(event)
        assert "agent-2" in recipients

    def test_entity_claim(self):
        """Test entity claiming for conflict prevention."""
        hub = SharingHub()
        
        # First claim should succeed
        assert hub.claim_entity("agent-1", "entity-123")
        
        # Second claim by different agent should fail
        assert not hub.claim_entity("agent-2", "entity-123")
        
        # Same agent claiming again should succeed
        assert hub.claim_entity("agent-1", "entity-123")
        
        # Release and try again
        hub.release_entity("agent-1", "entity-123")
        assert hub.claim_entity("agent-2", "entity-123")

    def test_event_history(self):
        """Test event history tracking."""
        hub = SharingHub(history_size=10)
        
        for i in range(15):
            event = ContextEvent(
                source_agent_id="agent-1",
                action=f"action_{i}"
            )
            hub.publish_sync(event)
        
        # Should only keep last 10
        assert len(hub.event_history) == 10
        
        recent = hub.get_recent_events(limit=5)
        assert len(recent) == 5


class TestSharingAPI:
    """Tests for sharing API endpoints."""

    def test_connect_to_hub(self, client, api_key):
        """Test connecting to the sharing hub."""
        response = client.post(
            "/share/connect",
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "connected"

    def test_get_connected_agents(self, client, api_key):
        """Test listing connected agents."""
        # Connect first
        client.post("/share/connect", headers={"X-API-Key": api_key})
        
        response = client.get("/share/agents")
        assert response.status_code == 200
        assert "connected_agents" in response.json()

    def test_subscribe_to_events(self, client, api_key):
        """Test subscribing to events."""
        client.post("/share/connect", headers={"X-API-Key": api_key})
        
        response = client.post(
            "/share/subscribe",
            json={"topics": ["decision.made", "action.completed"]},
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
        assert "subscription_id" in response.json()

    def test_publish_event(self, client, api_key):
        """Test publishing a shared event."""
        client.post("/share/connect", headers={"X-API-Key": api_key})
        
        response = client.post(
            "/share/publish",
            json={
                "topic": "decision.made",
                "action": "test_decision",
                "description": "Made a test decision"
            },
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
        assert "event_id" in response.json()

    def test_claim_entity(self, client, api_key, api_key_2):
        """Test claiming an entity."""
        # First agent claims
        response = client.post(
            "/share/claim/test-entity-123",
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
        
        # Second agent tries to claim - should fail
        response = client.post(
            "/share/claim/test-entity-123",
            headers={"X-API-Key": api_key_2}
        )
        assert response.status_code == 409  # Conflict

    def test_query_shared_context(self, client, api_key):
        """Test querying shared context."""
        client.post("/share/connect", headers={"X-API-Key": api_key})
        
        # Publish some events
        client.post(
            "/share/publish",
            json={"action": "customer_research", "description": "Researched customer needs"},
            headers={"X-API-Key": api_key}
        )
        
        # Query
        response = client.get("/share/query?q=customer")
        assert response.status_code == 200
        assert "events" in response.json()
