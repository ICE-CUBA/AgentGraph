"""
Basic tests for AgentGraph.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentgraph.core.schema import Agent, Event, EventType, Entity, EntityType
from agentgraph.storage.database import Database


def test_database():
    """Test database operations."""
    import tempfile
    import os
    # Use temp file database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(db_path)
    
    # Create agent
    agent = Agent(name="TestAgent", platform="test")
    db.create_agent(agent)
    print(f"✅ Created agent: {agent.id}")
    
    # Retrieve agent
    retrieved = db.get_agent(agent.id)
    assert retrieved is not None
    assert retrieved.name == "TestAgent"
    print(f"✅ Retrieved agent: {retrieved.name}")
    
    # Create event
    event = Event(
        type=EventType.TOOL_CALL,
        agent_id=agent.id,
        action="test_action",
        description="Test event",
        input_data={"key": "value"}
    )
    db.create_event(event)
    print(f"✅ Created event: {event.id}")
    
    # List events
    events = db.list_events(agent_id=agent.id)
    assert len(events) == 1
    print(f"✅ Listed events: {len(events)}")
    
    # Create entity
    entity = Entity(
        type=EntityType.DOCUMENT,
        name="test.txt",
        metadata={"size": 100}
    )
    db.create_entity(entity)
    print(f"✅ Created entity: {entity.id}")
    
    # Get stats
    stats = db.get_agent_stats(agent.id)
    assert stats["total_events"] == 1
    print(f"✅ Agent stats: {stats}")
    
    # Cleanup
    os.unlink(db_path)
    
    print("\n🎉 All tests passed!")


def test_schema():
    """Test schema serialization."""
    # Event to dict and back
    event = Event(
        type=EventType.DECISION,
        agent_id="agent-123",
        action="choose_action",
        description="Decided to proceed",
        metadata={"confidence": 0.95}
    )
    
    event_dict = event.to_dict()
    restored = Event.from_dict(event_dict)
    
    assert restored.type == event.type
    assert restored.agent_id == event.agent_id
    assert restored.action == event.action
    print("✅ Event serialization works")
    
    # Entity to dict and back
    entity = Entity(
        type=EntityType.USER,
        name="John Doe",
        metadata={"email": "john@example.com"}
    )
    
    entity_dict = entity.to_dict()
    restored_entity = Entity.from_dict(entity_dict)
    
    assert restored_entity.type == entity.type
    assert restored_entity.name == entity.name
    print("✅ Entity serialization works")
    
    print("\n🎉 Schema tests passed!")


if __name__ == "__main__":
    print("=" * 50)
    print("AgentGraph Tests")
    print("=" * 50)
    print("\n📋 Testing Schema...")
    test_schema()
    print("\n📋 Testing Database...")
    test_database()
