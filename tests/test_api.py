"""
Tests for AgentGraph API
"""

import pytest
from fastapi.testclient import TestClient

from agentgraph.api.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestAgentEndpoints:
    """Tests for agent endpoints."""

    def test_create_agent(self, client):
        """Test creating an agent."""
        response = client.post("/agents", json={
            "name": "TestAgent",
            "platform": "test"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TestAgent"
        assert "api_key" in data
        assert "id" in data

    def test_list_agents(self, client):
        """Test listing agents."""
        # Create an agent first
        client.post("/agents", json={"name": "Agent1", "platform": "test"})
        
        response = client.get("/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestEventEndpoints:
    """Tests for event endpoints."""

    def test_create_event_requires_auth(self, client):
        """Test that creating event requires API key."""
        response = client.post("/events", json={
            "type": "tool.call",
            "action": "test"
        })
        assert response.status_code == 422  # Missing header

    def test_create_event_with_auth(self, client):
        """Test creating event with valid API key."""
        # Create agent first
        agent_response = client.post("/agents", json={
            "name": "TestAgent",
            "platform": "test"
        })
        api_key = agent_response.json()["api_key"]
        
        # Create event
        response = client.post(
            "/events",
            json={
                "type": "tool.call",
                "action": "search",
                "description": "Test event"
            },
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "search"
        assert "id" in data

    def test_list_events(self, client):
        """Test listing events."""
        response = client.get("/events")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestQueryEndpoints:
    """Tests for query endpoints."""

    def test_query_graph(self, client):
        """Test querying the graph."""
        response = client.post("/query", json={
            "question": "what tools were used?"
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "question" in data

    def test_search_events(self, client):
        """Test searching events."""
        response = client.get("/search/events?q=test")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_search_entities(self, client):
        """Test searching entities."""
        response = client.get("/search/entities?q=test")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestGraphEndpoints:
    """Tests for graph endpoints."""

    def test_get_graph_data(self, client):
        """Test getting graph data for visualization."""
        response = client.get("/graph/data")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "links" in data
        assert "stats" in data
