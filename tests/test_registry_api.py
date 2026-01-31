"""
Tests for Registry API Routes.
"""

import pytest
from fastapi.testclient import TestClient

from agentgraph.api.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRegistryAgentEndpoints:
    """Test /registry/agents endpoints."""
    
    def test_register_agent(self, client):
        """Test agent registration."""
        response = client.post("/registry/agents", json={
            "name": "TestBot",
            "description": "A test bot",
            "capabilities": [
                {"name": "search", "metadata": {}},
                {"name": "translate", "metadata": {"languages": ["en", "es"]}}
            ]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TestBot"
        assert data["status"] == "online"
        assert len(data["capabilities"]) == 2
    
    def test_list_agents(self, client):
        """Test listing agents."""
        # Register an agent first
        client.post("/registry/agents", json={
            "name": "ListTestBot",
            "capabilities": []
        })
        
        response = client.get("/registry/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_agent(self, client):
        """Test getting specific agent."""
        # Register first
        reg_response = client.post("/registry/agents", json={
            "name": "GetTestBot",
            "capabilities": []
        })
        agent_id = reg_response.json()["id"]
        
        response = client.get(f"/registry/agents/{agent_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "GetTestBot"
    
    def test_get_nonexistent_agent(self, client):
        """Test getting agent that doesn't exist."""
        response = client.get("/registry/agents/fake-id-12345")
        assert response.status_code == 404
    
    def test_discover_by_capability(self, client):
        """Test discovering agents by capability."""
        # Register agent with capability
        client.post("/registry/agents", json={
            "name": "TranslatorBot",
            "capabilities": [{"name": "translate", "metadata": {}}]
        })
        
        response = client.get("/registry/agents", params={"capability": "translate"})
        assert response.status_code == 200
        data = response.json()
        assert any(a["name"] == "TranslatorBot" for a in data)
    
    def test_heartbeat(self, client):
        """Test heartbeat endpoint."""
        # Register first
        reg_response = client.post("/registry/agents", json={
            "name": "HeartbeatBot",
            "capabilities": []
        })
        agent_id = reg_response.json()["id"]
        
        response = client.post(f"/registry/agents/{agent_id}/heartbeat")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_heartbeat_nonexistent(self, client):
        """Test heartbeat for nonexistent agent."""
        response = client.post("/registry/agents/fake-id/heartbeat")
        assert response.status_code == 404
    
    def test_update_status(self, client):
        """Test status update."""
        # Register first
        reg_response = client.post("/registry/agents", json={
            "name": "StatusBot",
            "capabilities": []
        })
        agent_id = reg_response.json()["id"]
        
        response = client.patch(
            f"/registry/agents/{agent_id}/status",
            json={"status": "busy"}
        )
        assert response.status_code == 200
        
        # Verify status changed
        get_response = client.get(f"/registry/agents/{agent_id}")
        assert get_response.json()["status"] == "busy"
    
    def test_update_status_invalid(self, client):
        """Test invalid status update."""
        reg_response = client.post("/registry/agents", json={
            "name": "InvalidStatusBot",
            "capabilities": []
        })
        agent_id = reg_response.json()["id"]
        
        response = client.patch(
            f"/registry/agents/{agent_id}/status",
            json={"status": "invalid_status"}
        )
        assert response.status_code == 400
    
    def test_delete_agent(self, client):
        """Test agent deletion."""
        # Register first
        reg_response = client.post("/registry/agents", json={
            "name": "DeleteBot",
            "capabilities": []
        })
        agent_id = reg_response.json()["id"]
        
        response = client.delete(f"/registry/agents/{agent_id}")
        assert response.status_code == 200
        
        # Verify deleted
        get_response = client.get(f"/registry/agents/{agent_id}")
        assert get_response.status_code == 404


class TestRegistryStats:
    """Test /registry/stats endpoint."""
    
    def test_get_stats(self, client):
        """Test stats endpoint."""
        response = client.get("/registry/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_agents" in data
        assert "online_agents" in data
        assert "offline_agents" in data


class TestRegistryCleanup:
    """Test /registry/cleanup endpoint."""
    
    def test_cleanup_stale(self, client):
        """Test stale agent cleanup."""
        response = client.post("/registry/cleanup")
        assert response.status_code == 200
        assert "agents_marked_offline" in response.json()


class TestReputationEndpoints:
    """Test reputation-related endpoints."""
    
    def test_start_task(self, client):
        """Test starting a task."""
        response = client.post("/registry/tasks/start", json={
            "agent_id": "agent-123",
            "task_type": "translate"
        })
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "started"
    
    def test_complete_task(self, client):
        """Test completing a task."""
        # Start first
        start_response = client.post("/registry/tasks/start", json={
            "agent_id": "agent-456",
            "task_type": "search"
        })
        task_id = start_response.json()["task_id"]
        
        response = client.post(f"/registry/tasks/{task_id}/complete", json={
            "outcome": "success"
        })
        assert response.status_code == 200
        assert response.json()["outcome"] == "success"
    
    def test_complete_task_invalid_outcome(self, client):
        """Test completing with invalid outcome."""
        start_response = client.post("/registry/tasks/start", json={
            "agent_id": "agent-789",
            "task_type": "test"
        })
        task_id = start_response.json()["task_id"]
        
        response = client.post(f"/registry/tasks/{task_id}/complete", json={
            "outcome": "invalid"
        })
        assert response.status_code == 400
    
    def test_rate_task(self, client):
        """Test rating a task."""
        # Start and complete first
        start_response = client.post("/registry/tasks/start", json={
            "agent_id": "agent-rate",
            "task_type": "test"
        })
        task_id = start_response.json()["task_id"]
        
        client.post(f"/registry/tasks/{task_id}/complete", json={
            "outcome": "success"
        })
        
        response = client.post(f"/registry/tasks/{task_id}/rate", json={
            "rating": 0.9,
            "rated_by": "reviewer-agent"
        })
        assert response.status_code == 200
    
    def test_get_agent_reputation(self, client):
        """Test getting agent reputation."""
        response = client.get("/registry/agents/some-agent/reputation")
        assert response.status_code == 200
        data = response.json()
        assert "trust_score" in data
        assert "total_tasks" in data
    
    def test_get_agent_trust(self, client):
        """Test getting just trust score."""
        response = client.get("/registry/agents/some-agent/trust")
        assert response.status_code == 200
        data = response.json()
        assert "trust_score" in data
    
    def test_leaderboard(self, client):
        """Test leaderboard endpoint."""
        response = client.get("/registry/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
