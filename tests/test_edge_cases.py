"""
Edge case and error handling tests.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


class TestRegistryEdgeCases:
    """Test edge cases in Registry."""
    
    def test_register_duplicate_id(self):
        """Test registering agent with same ID twice."""
        from agentgraph.registry import AgentRegistry
        from agentgraph.registry.models import Agent
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            registry = AgentRegistry(db_path=db_path)
            
            agent1 = Agent(id="same-id", name="Bot1")
            agent2 = Agent(id="same-id", name="Bot2")
            
            registry.register(agent1)
            registry.register(agent2)  # Should update, not error
            
            result = registry.get("same-id")
            assert result.name == "Bot2"  # Should be updated
        finally:
            os.unlink(db_path)
    
    def test_discover_no_results(self):
        """Test discovery when no agents match."""
        from agentgraph.registry import AgentRegistry
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            registry = AgentRegistry(db_path=db_path)
            results = registry.discover(capability="nonexistent_capability")
            assert results == []
        finally:
            os.unlink(db_path)
    
    def test_capability_with_empty_metadata(self):
        """Test capability matching with empty metadata."""
        from agentgraph.registry.models import Capability
        
        cap = Capability("test", metadata={})
        
        # Should match name only
        assert cap.matches("test")
        # Should fail if filtering by non-existent key
        assert not cap.matches("test", language="en")
    
    def test_agent_status_transitions(self):
        """Test all agent status transitions."""
        from agentgraph.registry import AgentRegistry, AgentStatus
        from agentgraph.registry.models import Agent
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            registry = AgentRegistry(db_path=db_path)
            agent = Agent(id="transition-test", name="TransitionBot")
            registry.register(agent)
            
            # Test all transitions
            for status in AgentStatus:
                registry.update_status("transition-test", status)
                result = registry.get("transition-test")
                assert result.status == status
        finally:
            os.unlink(db_path)


class TestReputationEdgeCases:
    """Test edge cases in Reputation system."""
    
    def test_rate_task_boundary_values(self):
        """Test rating with boundary values."""
        from agentgraph.registry.reputation import ReputationTracker, TaskOutcome
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            tracker = ReputationTracker(db_path=db_path)
            
            # Test rating of 0.0
            task_id = tracker.record_task_start("agent", "task")
            tracker.record_task_complete(task_id, TaskOutcome.SUCCESS)
            assert tracker.rate_task(task_id, 0.0)
            
            # Test rating of 1.0
            task_id2 = tracker.record_task_start("agent", "task")
            tracker.record_task_complete(task_id2, TaskOutcome.SUCCESS)
            assert tracker.rate_task(task_id2, 1.0)
        finally:
            os.unlink(db_path)
    
    def test_trust_score_with_no_tasks(self):
        """Test trust score for agent with no tasks."""
        from agentgraph.registry.reputation import ReputationTracker
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            tracker = ReputationTracker(db_path=db_path)
            score = tracker.get_trust_score("nonexistent-agent")
            assert score == 0.5  # Neutral default
        finally:
            os.unlink(db_path)
    
    def test_all_task_outcomes(self):
        """Test all task outcome types."""
        from agentgraph.registry.reputation import ReputationTracker, TaskOutcome
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            tracker = ReputationTracker(db_path=db_path)
            
            for outcome in TaskOutcome:
                task_id = tracker.record_task_start("agent", "test")
                result = tracker.record_task_complete(task_id, outcome)
                assert result is True
        finally:
            os.unlink(db_path)


class TestAPIEdgeCases:
    """Test API edge cases."""
    
    @pytest.fixture
    def client(self):
        from agentgraph.api.server import app
        return TestClient(app)
    
    def test_invalid_json(self, client):
        """Test API with invalid JSON."""
        response = client.post(
            "/registry/agents",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test API with missing required fields."""
        response = client.post("/registry/agents", json={})
        assert response.status_code == 422
    
    def test_empty_capabilities_list(self, client):
        """Test registering agent with empty capabilities."""
        response = client.post("/registry/agents", json={
            "name": "EmptyCapBot",
            "capabilities": []
        })
        assert response.status_code == 200
        assert response.json()["capabilities"] == []
    
    def test_very_long_name(self, client):
        """Test registering agent with very long name."""
        long_name = "A" * 1000
        response = client.post("/registry/agents", json={
            "name": long_name,
            "capabilities": []
        })
        assert response.status_code == 200
        assert response.json()["name"] == long_name
    
    def test_unicode_in_name(self, client):
        """Test registering agent with unicode name."""
        response = client.post("/registry/agents", json={
            "name": "翻译机器人 🤖",
            "capabilities": []
        })
        assert response.status_code == 200
        assert "翻译" in response.json()["name"]


class TestConcurrency:
    """Test concurrent access patterns."""
    
    def test_concurrent_registrations(self):
        """Test concurrent agent registrations."""
        import threading
        from agentgraph.registry import AgentRegistry
        from agentgraph.registry.models import Agent
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            registry = AgentRegistry(db_path=db_path)
            errors = []
            
            def register_agent(i):
                try:
                    agent = Agent(id=f"agent-{i}", name=f"Bot{i}")
                    registry.register(agent)
                except Exception as e:
                    errors.append(e)
            
            threads = [threading.Thread(target=register_agent, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            assert len(errors) == 0
            assert registry.count() == 10
        finally:
            os.unlink(db_path)


class TestSchemaValidation:
    """Test data schema validation."""
    
    def test_capability_from_dict_missing_name(self):
        """Test Capability.from_dict with missing name."""
        from agentgraph.registry.models import Capability
        
        with pytest.raises(KeyError):
            Capability.from_dict({})
    
    def test_agent_serialization_roundtrip(self):
        """Test Agent serialization and deserialization."""
        from agentgraph.registry.models import Agent, Capability, AgentStatus
        
        original = Agent(
            id="test-id",
            name="TestBot",
            description="A test bot",
            capabilities=[Capability("cap1"), Capability("cap2", {"key": "value"})],
            status=AgentStatus.BUSY,
            endpoint="http://test:8000",
            metadata={"custom": "data"}
        )
        
        serialized = original.to_dict()
        restored = Agent.from_dict(serialized)
        
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.status == original.status
        assert len(restored.capabilities) == len(original.capabilities)


class TestErrorRecovery:
    """Test error recovery scenarios."""
    
    def test_database_corruption_recovery(self):
        """Test handling of corrupted database."""
        from agentgraph.registry import AgentRegistry
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
            # Write garbage to simulate corruption
            f.write(b"garbage data")
        
        try:
            # Should handle gracefully (SQLite will recreate or error)
            # This tests that we don't crash
            with pytest.raises(Exception):
                registry = AgentRegistry(db_path=db_path)
                registry.list_all()
        finally:
            os.unlink(db_path)
