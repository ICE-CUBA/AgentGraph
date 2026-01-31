"""
Tests for AgentGraph SDK
"""

import pytest
from unittest.mock import patch, MagicMock

from agentgraph import AgentGraphClient
from agentgraph.core.schema import Event, EventType, Entity, EntityType


class TestAgentGraphClient:
    """Tests for the SDK client."""

    @patch('agentgraph.sdk.client.requests')
    def test_client_init(self, mock_requests):
        """Test client initialization."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "session-123"}
        mock_requests.request.return_value = mock_response
        
        client = AgentGraphClient(
            api_key="test-key",
            base_url="http://localhost:8080",
            auto_session=False
        )
        
        assert client.api_key == "test-key"
        assert client.base_url == "http://localhost:8080"

    @patch('agentgraph.sdk.client.requests')
    def test_log_event(self, mock_requests):
        """Test logging an event."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "event-123"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.request.return_value = mock_response
        
        client = AgentGraphClient(
            api_key="test-key",
            auto_session=False
        )
        
        event_id = client.log(
            event_type="tool.call",
            action="search",
            input_data={"query": "test"}
        )
        
        assert event_id == "event-123"

    @patch('agentgraph.sdk.client.requests')
    def test_create_entity(self, mock_requests):
        """Test creating an entity."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "entity-123"}
        mock_response.raise_for_status = MagicMock()
        mock_requests.request.return_value = mock_response
        
        client = AgentGraphClient(
            api_key="test-key",
            auto_session=False
        )
        
        entity_id = client.create_entity(
            entity_type="user",
            name="Alice",
            metadata={"role": "admin"}
        )
        
        assert entity_id == "entity-123"

    @patch('agentgraph.sdk.client.requests')
    def test_query(self, mock_requests):
        """Test querying the graph."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "question": "what tools?",
            "answer": "Found 5 tool calls",
            "events": []
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.request.return_value = mock_response
        
        client = AgentGraphClient(
            api_key="test-key",
            auto_session=False
        )
        
        result = client.query("what tools were used?")
        
        assert result["answer"] == "Found 5 tool calls"


class TestSchema:
    """Tests for core schema."""

    def test_event_creation(self):
        """Test creating an Event."""
        event = Event(
            type=EventType.TOOL_CALL,
            agent_id="agent-123",
            action="search",
            description="Searching for data"
        )
        
        assert event.type == EventType.TOOL_CALL
        assert event.agent_id == "agent-123"
        assert event.action == "search"

    def test_event_to_dict(self):
        """Test Event serialization."""
        event = Event(
            type=EventType.DECISION,
            agent_id="agent-123",
            action="choose_tool"
        )
        
        data = event.to_dict()
        
        assert data["type"] == "decision"
        assert data["agent_id"] == "agent-123"
        assert "id" in data
        assert "timestamp" in data

    def test_entity_creation(self):
        """Test creating an Entity."""
        entity = Entity(
            type=EntityType.USER,
            name="Alice",
            metadata={"email": "alice@example.com"}
        )
        
        assert entity.type == EntityType.USER
        assert entity.name == "Alice"
        assert entity.metadata["email"] == "alice@example.com"
