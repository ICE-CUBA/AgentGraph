#!/usr/bin/env python3
"""
AgentGraph Demo Script

Demonstrates the SDK and populates sample data.
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
    return data['api_key']


def run_demo(api_key: str):
    """Run demo with sample events."""
    client = AgentGraphClient(
        api_key=api_key,
        base_url=BASE_URL,
        session_name="Demo Session"
    )
    
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
        time.sleep(random.uniform(0.1, 0.5))
        duration = random.randint(50, 500)
        
        event_id = client.log(
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
    print(f"   ✓ action.error: failed_operation")
    
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
    print(f"   ✓ Context manager with nested events")
    
    print("\n🎉 Demo complete! Open http://localhost:8080 to see the dashboard.")


def main():
    print("=" * 50)
    print("🧠 AgentGraph Demo")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            raise Exception("Server not healthy")
    except:
        print("\n❌ Server not running!")
        print("   Start it with: python -m agentgraph.api.server")
        return
    
    print("\n✅ Server is running")
    
    # Setup and run demo
    api_key = setup_agent()
    run_demo(api_key)


if __name__ == "__main__":
    main()
