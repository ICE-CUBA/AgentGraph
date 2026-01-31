#!/usr/bin/env python3
"""
AgentGraph Demo Script

Demonstrates the SDK and populates sample data including entities and relationships.
"""

import time
import random
from agentgraph import AgentGraphClient

# First, register an agent via API
import requests

BASE_URL = "http://localhost:8080"

def setup_agent():
    """Register a demo agent."""
    response = requests.post(f"{BASE_URL}/agents", json={
        "name": "DemoAgent",
        "platform": "demo",
        "capabilities": ["search", "summarize", "analyze"]
    })
    data = response.json()
    print(f"✅ Registered agent: {data['name']}")
    print(f"   API Key: {data['api_key']}")
    return data


def run_demo(agent_data: dict):
    """Run demo with sample events, entities, and relationships."""
    client = AgentGraphClient(
        api_key=agent_data['api_key'],
        base_url=BASE_URL,
        session_name="Demo Session"
    )
    
    print("\n🔷 Creating entities for the graph...")
    
    # Create some users
    user1_id = client.create_entity("user", "Alice", {"role": "admin"})
    user2_id = client.create_entity("user", "Bob", {"role": "developer"})
    print("   ✓ Created users: Alice, Bob")
    
    # Create tasks
    task1_id = client.create_entity("task", "Data Analysis", {"priority": "high"})
    task2_id = client.create_entity("task", "Report Generation", {"priority": "medium"})
    task3_id = client.create_entity("task", "API Integration", {"priority": "low"})
    print("   ✓ Created tasks: Data Analysis, Report Generation, API Integration")
    
    # Create tools
    tool1_id = client.create_entity("tool", "search", {"version": "1.0"})
    tool2_id = client.create_entity("tool", "summarize", {"version": "2.1"})
    tool3_id = client.create_entity("tool", "analyze", {"version": "1.5"})
    print("   ✓ Created tools: search, summarize, analyze")
    
    # Create documents
    doc1_id = client.create_entity("document", "Q4 Report", {"type": "pdf"})
    doc2_id = client.create_entity("document", "API Docs", {"type": "markdown"})
    print("   ✓ Created documents: Q4 Report, API Docs")
    
    # Create resources
    res1_id = client.create_entity("resource", "Database", {"type": "postgres"})
    res2_id = client.create_entity("resource", "Cache", {"type": "redis"})
    print("   ✓ Created resources: Database, Cache")
    
    print("\n🔗 Creating relationships...")
    
    # Users own tasks
    client.create_relationship(user1_id, task1_id, "owns", {"assigned": "2024-01-15"})
    client.create_relationship(user2_id, task2_id, "owns", {"assigned": "2024-01-16"})
    client.create_relationship(user2_id, task3_id, "owns", {"assigned": "2024-01-17"})
    print("   ✓ Users assigned to tasks")
    
    # Tasks depend on each other
    client.create_relationship(task2_id, task1_id, "depends_on", {"blocking": True})
    print("   ✓ Task dependencies")
    
    # Tasks use tools
    client.create_relationship(task1_id, tool3_id, "referenced", {"usage": "primary"})
    client.create_relationship(task1_id, tool1_id, "referenced", {"usage": "secondary"})
    client.create_relationship(task2_id, tool2_id, "referenced", {"usage": "primary"})
    client.create_relationship(task3_id, tool1_id, "referenced", {"usage": "primary"})
    print("   ✓ Tasks linked to tools")
    
    # Documents created by tasks
    client.create_relationship(task1_id, doc1_id, "created")
    client.create_relationship(task3_id, doc2_id, "created")
    print("   ✓ Tasks created documents")
    
    # Tools access resources
    client.create_relationship(tool1_id, res1_id, "referenced", {"type": "read"})
    client.create_relationship(tool3_id, res1_id, "referenced", {"type": "read"})
    client.create_relationship(tool3_id, res2_id, "referenced", {"type": "cache"})
    print("   ✓ Tools linked to resources")
    
    # Users collaborate
    client.create_relationship(user1_id, user2_id, "collaborated_with", {"project": "Q4 Analysis"})
    print("   ✓ User collaboration")
    
    print("\n📊 Logging sample events...")
    
    # Simulate agent workflow
    actions = [
        ("tool.call", "search", {"query": "AI news 2024"}),
        ("decision", "analyze_results", None),
        ("tool.call", "summarize", {"text": "Multiple articles found..."}),
        ("message.sent", "respond", {"content": "Here's what I found..."}),
        ("tool.call", "save_memory", {"key": "last_search", "value": "AI news"}),
    ]
    
    for event_type, action, input_data in actions:
        # Random delay to simulate work
        time.sleep(random.uniform(0.1, 0.3))
        duration = random.randint(50, 500)
        
        client.log(
            event_type=event_type,
            action=action,
            input_data=input_data,
            duration_ms=duration,
            description=f"Demo event: {action}"
        )
        print(f"   ✓ {event_type}: {action} ({duration}ms)")
    
    # Simulate an error
    client.log(
        event_type="action.error",
        action="failed_operation",
        status="error",
        error_message="Connection timeout",
        description="Demo error event"
    )
    print("   ✓ action.error: failed_operation")
    
    # Use decorator example
    @client.track(event_type="tool.call", action="decorated_function")
    def process_data(x, y):
        time.sleep(0.1)
        return x + y
    
    result = process_data(10, 20)
    print(f"   ✓ Decorated function returned: {result}")
    
    # Use context manager
    with client.track_context("complex_operation"):
        time.sleep(0.2)
        client.log("tool.call", action="nested_step_1")
        time.sleep(0.1)
        client.log("tool.call", action="nested_step_2")
    print("   ✓ Context manager with nested events")
    
    print("\n" + "=" * 50)
    print("🔍 Testing Agent Query Interface")
    print("=" * 50)
    
    # Demo the query interface
    queries = [
        "what tools were used?",
        "show me errors",
        "what happened to Alice?",
        "what did the agent do recently?"
    ]
    
    for question in queries:
        result = client.query(question)
        print(f"\n❓ {question}")
        print(f"   💬 {result['answer']}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo complete!")
    print("=" * 50)
    print("\n📌 Open http://localhost:8080 to see the dashboard")
    print("   📊 Events tab - Real-time agent activity")
    print("   🕸️ Graph tab - Entity relationship visualization")
    print("   🔍 Query API - Ask questions about agent activity")
    print("\n💡 Try in Python:")
    print("   from agentgraph import AgentGraphClient")
    print("   client = AgentGraphClient(api_key='...')")
    print("   client.query('what happened to customer X?')")


def main():
    print("=" * 50)
    print("🧠 AgentGraph Demo")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            raise Exception("Server not healthy")
    except Exception:
        print("\n❌ Server not running!")
        print("   Start it with: python -m agentgraph.api.server")
        return
    
    print("\n✅ Server is running")
    
    # Setup and run demo
    agent_data = setup_agent()
    run_demo(agent_data)


if __name__ == "__main__":
    main()
