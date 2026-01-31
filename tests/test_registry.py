"""
Tests for Agent Registry.
"""

import pytest
import tempfile
import os
from pathlib import Path

from agentgraph.registry import (
    AgentRegistry,
    Agent,
    Capability,
    AgentStatus,
    register_agent,
    discover_agents,
    get_agent,
    heartbeat,
    update_status,
    unregister_agent,
)


@pytest.fixture
def temp_registry():
    """Create a registry with a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    registry = AgentRegistry(db_path=db_path)
    yield registry
    
    # Cleanup
    os.unlink(db_path)


class TestCapability:
    """Test Capability model."""
    
    def test_simple_match(self):
        cap = Capability("translate")
        assert cap.matches("translate")
        assert cap.matches("TRANSLATE")  # Case insensitive
        assert not cap.matches("summarize")
    
    def test_metadata_match(self):
        cap = Capability("translate", {"languages": ["en", "es", "fr"]})
        assert cap.matches("translate", languages="en")
        assert cap.matches("translate", languages="es")
        assert not cap.matches("translate", languages="de")
    
    def test_serialization(self):
        cap = Capability("code_review", {"languages": ["python"]})
        d = cap.to_dict()
        cap2 = Capability.from_dict(d)
        assert cap.name == cap2.name
        assert cap.metadata == cap2.metadata


class TestAgent:
    """Test Agent model."""
    
    def test_has_capability(self):
        agent = Agent(
            id="test-1",
            name="TestBot",
            capabilities=[
                Capability("translate", {"languages": ["en", "es"]}),
                Capability("summarize"),
            ]
        )
        
        assert agent.has_capability("translate")
        assert agent.has_capability("translate", languages="en")
        assert not agent.has_capability("translate", languages="de")
        assert agent.has_capability("summarize")
        assert not agent.has_capability("code_review")
    
    def test_is_online(self):
        agent = Agent(id="test-1", name="TestBot")
        
        agent.status = AgentStatus.ONLINE
        assert agent.is_online()
        
        agent.status = AgentStatus.BUSY
        assert agent.is_online()
        
        agent.status = AgentStatus.OFFLINE
        assert not agent.is_online()


class TestAgentRegistry:
    """Test AgentRegistry."""
    
    def test_register_and_get(self, temp_registry):
        agent = Agent(
            id="agent-1",
            name="ResearchBot",
            description="Does research",
            capabilities=[Capability("web_search")],
        )
        
        registered = temp_registry.register(agent)
        assert registered.id == "agent-1"
        assert registered.status == AgentStatus.ONLINE
        
        retrieved = temp_registry.get("agent-1")
        assert retrieved is not None
        assert retrieved.name == "ResearchBot"
        assert retrieved.has_capability("web_search")
    
    def test_discover_by_capability(self, temp_registry):
        # Register multiple agents
        temp_registry.register(Agent(
            id="translator",
            name="TranslatorBot",
            capabilities=[Capability("translate", {"languages": ["en", "es"]})]
        ))
        temp_registry.register(Agent(
            id="summarizer",
            name="SummarizerBot",
            capabilities=[Capability("summarize")]
        ))
        temp_registry.register(Agent(
            id="multi",
            name="MultiBot",
            capabilities=[Capability("translate"), Capability("summarize")]
        ))
        
        # Find translators
        translators = temp_registry.discover(capability="translate")
        assert len(translators) == 2
        
        # Find summarizers
        summarizers = temp_registry.discover(capability="summarize")
        assert len(summarizers) == 2
        
        # Find with specific language
        spanish = temp_registry.discover(capability="translate", languages="es")
        assert len(spanish) == 1
        assert spanish[0].id == "translator"
    
    def test_heartbeat(self, temp_registry):
        agent = Agent(id="agent-1", name="TestBot")
        temp_registry.register(agent)
        
        # Update last_seen
        result = temp_registry.heartbeat("agent-1")
        assert result is True
        
        # Non-existent agent
        result = temp_registry.heartbeat("fake-agent")
        assert result is False
    
    def test_update_status(self, temp_registry):
        agent = Agent(id="agent-1", name="TestBot")
        temp_registry.register(agent)
        
        temp_registry.update_status("agent-1", AgentStatus.BUSY)
        retrieved = temp_registry.get("agent-1")
        assert retrieved.status == AgentStatus.BUSY
        
        temp_registry.update_status("agent-1", AgentStatus.OFFLINE)
        retrieved = temp_registry.get("agent-1")
        assert retrieved.status == AgentStatus.OFFLINE
    
    def test_unregister(self, temp_registry):
        agent = Agent(id="agent-1", name="TestBot")
        temp_registry.register(agent)
        
        assert temp_registry.get("agent-1") is not None
        
        result = temp_registry.unregister("agent-1")
        assert result is True
        
        assert temp_registry.get("agent-1") is None
        
        # Already removed
        result = temp_registry.unregister("agent-1")
        assert result is False
    
    def test_count(self, temp_registry):
        assert temp_registry.count() == 0
        
        temp_registry.register(Agent(id="a1", name="Bot1"))
        temp_registry.register(Agent(id="a2", name="Bot2"))
        
        assert temp_registry.count() == 2
        assert temp_registry.count(online_only=True) == 2
        
        temp_registry.update_status("a1", AgentStatus.OFFLINE)
        assert temp_registry.count() == 2
        assert temp_registry.count(online_only=True) == 1


class TestClientAPI:
    """Test the high-level client API."""
    
    def test_register_agent_simple(self):
        agent = register_agent(
            name="TestAgent",
            capabilities=["search", "summarize"],
            description="A test agent"
        )
        
        assert agent.name == "TestAgent"
        assert len(agent.capabilities) == 2
        assert agent.has_capability("search")
    
    def test_discover_agents(self):
        # Register an agent
        agent = register_agent(
            name="DiscoverableAgent",
            capabilities=["unique_cap_12345"],
        )
        
        # Find it
        found = discover_agents("unique_cap_12345", online_only=True)
        assert len(found) >= 1
        assert any(a.id == agent.id for a in found)
    
    def test_heartbeat_and_status(self):
        agent = register_agent(name="HeartbeatTest")
        
        assert heartbeat(agent.id)
        assert update_status(agent.id, "busy")
        
        retrieved = get_agent(agent.id)
        assert retrieved.status == AgentStatus.BUSY
