"""
Integration Tests - End-to-end workflows.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

from agentgraph.api.server import app
from agentgraph.registry import AgentRegistry, ReputationTracker
from agentgraph.registry.reputation import TaskOutcome


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_registry():
    """Create registry with temp database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    registry = AgentRegistry(db_path=db_path)
    yield registry
    os.unlink(db_path)


@pytest.fixture
def temp_reputation():
    """Create reputation tracker with temp database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    tracker = ReputationTracker(db_path=db_path)
    yield tracker
    os.unlink(db_path)


class TestMultiAgentDiscoveryFlow:
    """Test: Agent A registers → Agent B discovers → They collaborate."""
    
    def test_register_discover_collaborate(self, client):
        """Full multi-agent discovery flow."""
        # Step 1: Agent A registers as a translator
        reg_response = client.post("/registry/agents", json={
            "name": "TranslatorAgent",
            "description": "Translates text between languages",
            "capabilities": [
                {"name": "translate", "metadata": {"languages": ["en", "es", "fr"]}}
            ],
            "endpoint": "http://translator:8000"
        })
        assert reg_response.status_code == 200
        translator_id = reg_response.json()["id"]
        
        # Step 2: Agent B registers as a researcher
        client.post("/registry/agents", json={
            "name": "ResearchAgent",
            "capabilities": [{"name": "web_search", "metadata": {}}]
        })
        
        # Step 3: Agent B discovers translators
        discover_response = client.get("/registry/agents", params={
            "capability": "translate",
            "online_only": "true"
        })
        assert discover_response.status_code == 200
        translators = discover_response.json()
        assert len(translators) >= 1
        assert any(t["name"] == "TranslatorAgent" for t in translators)
        
        # Step 4: Agent B requests work from Agent A (task tracking)
        task_response = client.post("/registry/tasks/start", json={
            "agent_id": translator_id,
            "task_type": "translate",
            "metadata": {"from": "en", "to": "es"}
        })
        task_id = task_response.json()["task_id"]
        
        # Step 5: Agent A completes the work
        complete_response = client.post(f"/registry/tasks/{task_id}/complete", json={
            "outcome": "success"
        })
        assert complete_response.status_code == 200
        
        # Step 6: Agent B rates Agent A's work
        rate_response = client.post(f"/registry/tasks/{task_id}/rate", json={
            "rating": 0.95,
            "rated_by": "ResearchAgent"
        })
        assert rate_response.status_code == 200
        
        # Step 7: Check that Agent A's trust score increased
        trust_response = client.get(f"/registry/agents/{translator_id}/trust")
        trust_score = trust_response.json()["trust_score"]
        assert trust_score > 0.5  # Above neutral


class TestReputationBuilding:
    """Test: Agent builds reputation through successful work."""
    
    def test_reputation_increases_with_success(self, temp_registry, temp_reputation):
        """Test that completing tasks successfully increases trust."""
        from agentgraph.registry.models import Agent, Capability
        
        # Register agent
        agent = Agent(
            id="reliable-agent",
            name="ReliableBot",
            capabilities=[Capability("code_review")]
        )
        temp_registry.register(agent)
        
        # Initial trust
        initial_trust = temp_reputation.get_trust_score(agent.id)
        assert initial_trust == 0.5  # Neutral default
        
        # Complete 10 successful tasks
        for i in range(10):
            task_id = temp_reputation.record_task_start(agent.id, "code_review")
            temp_reputation.record_task_complete(task_id, TaskOutcome.SUCCESS)
            temp_reputation.rate_task(task_id, 0.9)
        
        # Trust should have increased
        final_trust = temp_reputation.get_trust_score(agent.id)
        assert final_trust > initial_trust
        assert final_trust > 0.6  # Significantly above neutral
    
    def test_reputation_decreases_with_failure(self, temp_reputation):
        """Test that failures decrease trust."""
        # Complete 5 failed tasks
        for i in range(5):
            task_id = temp_reputation.record_task_start("bad-agent", "task")
            temp_reputation.record_task_complete(task_id, TaskOutcome.FAILURE)
        
        trust = temp_reputation.get_trust_score("bad-agent")
        assert trust < 0.5  # Below neutral


class TestConflictPrevention:
    """Test: Agents claim resources to prevent conflicts."""
    
    def test_claim_prevents_double_work(self, client):
        """Test that claims prevent other agents from working on same entity."""
        # Create an agent
        from agentgraph.api.server import db
        from agentgraph.core.schema import Agent
        
        agent = Agent(name="ClaimAgent", platform="test")
        db.create_agent(agent)
        api_key = agent.api_key
        
        # Connect to sharing hub
        client.post("/share/connect", headers={"X-API-Key": api_key})
        
        # Claim an entity
        claim_response = client.post(
            "/share/claim/customer-42",
            headers={"X-API-Key": api_key}
        )
        assert claim_response.status_code == 200
        
        # Create second agent
        agent2 = Agent(name="ClaimAgent2", platform="test")
        db.create_agent(agent2)
        api_key2 = agent2.api_key
        
        client.post("/share/connect", headers={"X-API-Key": api_key2})
        
        # Second agent tries to claim same entity - should fail
        claim2_response = client.post(
            "/share/claim/customer-42",
            headers={"X-API-Key": api_key2}
        )
        assert claim2_response.status_code == 409  # Conflict
        
        # First agent releases
        client.post("/share/release/customer-42", headers={"X-API-Key": api_key})
        
        # Now second agent can claim
        claim3_response = client.post(
            "/share/claim/customer-42",
            headers={"X-API-Key": api_key2}
        )
        assert claim3_response.status_code == 200


class TestEventSharing:
    """Test: Agents share events in real-time."""
    
    def test_publish_and_query(self, client):
        """Test publishing and querying shared events."""
        from agentgraph.api.server import db
        from agentgraph.core.schema import Agent
        
        # Create agent
        agent = Agent(name="ShareAgent", platform="test")
        db.create_agent(agent)
        api_key = agent.api_key
        
        # Connect
        client.post("/share/connect", headers={"X-API-Key": api_key})
        
        # Publish event
        publish_response = client.post("/share/publish", 
            headers={"X-API-Key": api_key},
            json={
                "topic": "action.completed",
                "action": "research",
                "description": "Found important data",
                "data": {"key": "value"}
            }
        )
        assert publish_response.status_code == 200
        
        # Query events
        query_response = client.get("/share/query", params={"q": "research"})
        assert query_response.status_code == 200


class TestKnowledgeGraph:
    """Test: Building and querying knowledge graph."""
    
    def test_create_entities_and_relationships(self, client):
        """Test creating a knowledge graph."""
        from agentgraph.api.server import db
        from agentgraph.core.schema import Agent
        
        # Create agent for auth
        agent = Agent(name="GraphAgent", platform="test")
        db.create_agent(agent)
        api_key = agent.api_key
        
        # Create entities
        customer_response = client.post("/entities",
            headers={"X-API-Key": api_key},
            json={"type": "user", "name": "Acme Corp", "metadata": {"industry": "tech"}}
        )
        assert customer_response.status_code == 200
        customer_id = customer_response.json()["id"]
        
        project_response = client.post("/entities",
            headers={"X-API-Key": api_key},
            json={"type": "task", "name": "Q1 Analysis", "metadata": {"priority": "high"}}
        )
        project_id = project_response.json()["id"]
        
        # Create relationship
        rel_response = client.post("/relationships",
            headers={"X-API-Key": api_key},
            json={
                "source_entity_id": customer_id,
                "target_entity_id": project_id,
                "type": "owns"
            }
        )
        assert rel_response.status_code == 200
        
        # Query graph
        graph_response = client.get("/graph/data")
        assert graph_response.status_code == 200
        data = graph_response.json()
        assert data["stats"]["node_count"] >= 2
        assert data["stats"]["link_count"] >= 1


class TestAgentLifecycle:
    """Test: Full agent lifecycle from registration to cleanup."""
    
    def test_full_lifecycle(self, client):
        """Test agent registration, activity, and cleanup."""
        # Register
        reg_response = client.post("/registry/agents", json={
            "name": "LifecycleBot",
            "capabilities": [{"name": "test", "metadata": {}}]
        })
        agent_id = reg_response.json()["id"]
        
        # Verify online
        get_response = client.get(f"/registry/agents/{agent_id}")
        assert get_response.json()["status"] == "online"
        
        # Send heartbeat
        client.post(f"/registry/agents/{agent_id}/heartbeat")
        
        # Set to busy
        client.patch(f"/registry/agents/{agent_id}/status", json={"status": "busy"})
        assert client.get(f"/registry/agents/{agent_id}").json()["status"] == "busy"
        
        # Set to offline
        client.patch(f"/registry/agents/{agent_id}/status", json={"status": "offline"})
        assert client.get(f"/registry/agents/{agent_id}").json()["status"] == "offline"
        
        # Delete
        client.delete(f"/registry/agents/{agent_id}")
        assert client.get(f"/registry/agents/{agent_id}").status_code == 404
