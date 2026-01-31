#!/usr/bin/env python3
"""
Multi-Agent Collaboration Demo

Demonstrates how agents can share context and coordinate using AgentGraph.

This example shows:
1. Two agents connecting to the sharing hub
2. Subscribing to each other's events
3. Publishing context updates
4. Conflict prevention with entity claims
5. Querying shared history

Run:
    # Start the server first
    python -m agentgraph.api.server
    
    # Then run this demo
    python examples/multi_agent_demo.py
"""

import time
import requests

BASE_URL = "http://localhost:8080"


def create_agent(name: str, platform: str = "demo") -> dict:
    """Create a new agent and return its info."""
    response = requests.post(f"{BASE_URL}/agents", json={
        "name": name,
        "platform": platform,
        "capabilities": ["research", "analysis", "reporting"]
    })
    return response.json()


def main():
    print("=" * 60)
    print("🤖 Multi-Agent Collaboration Demo")
    print("=" * 60)
    
    # Check server
    try:
        health = requests.get(f"{BASE_URL}/health").json()
        print(f"\n✅ Server running: {health}")
    except Exception:
        print("\n❌ Server not running! Start with: python -m agentgraph.api.server")
        return
    
    # Create two agents
    print("\n📝 Creating agents...")
    agent1 = create_agent("ResearchAgent")
    agent2 = create_agent("AnalysisAgent")
    
    key1 = agent1["api_key"]
    key2 = agent2["api_key"]
    
    print(f"   ✓ Created: {agent1['name']} (ID: {agent1['id'][:8]}...)")
    print(f"   ✓ Created: {agent2['name']} (ID: {agent2['id'][:8]}...)")
    
    headers1 = {"X-API-Key": key1}
    headers2 = {"X-API-Key": key2}
    
    # Connect to sharing hub
    print("\n🔌 Connecting to sharing hub...")
    requests.post(f"{BASE_URL}/share/connect", headers=headers1)
    requests.post(f"{BASE_URL}/share/connect", headers=headers2)
    
    agents = requests.get(f"{BASE_URL}/share/agents").json()
    print(f"   ✓ {agents['count']} agents connected")
    
    # Subscribe to events
    print("\n📡 Setting up subscriptions...")
    
    # Agent 1 subscribes to decisions
    requests.post(f"{BASE_URL}/share/subscribe", 
        json={"topics": ["decision.made", "action.completed"]},
        headers=headers1
    )
    print("   ✓ ResearchAgent subscribed to: decision.made, action.completed")
    
    # Agent 2 subscribes to all
    requests.post(f"{BASE_URL}/share/subscribe",
        json={"topics": ["*"]},
        headers=headers2
    )
    print("   ✓ AnalysisAgent subscribed to: all events")
    
    # Simulate collaboration
    print("\n🔄 Simulating agent collaboration...")
    print("-" * 40)
    
    # Agent 1 starts research on a customer
    customer_id = "customer-42"
    
    # Claim the customer (conflict prevention)
    claim = requests.post(f"{BASE_URL}/share/claim/{customer_id}", headers=headers1)
    if claim.status_code == 200:
        print(f"\n[ResearchAgent] Claimed entity: {customer_id}")
    
    # Publish research findings
    pub1 = requests.post(f"{BASE_URL}/share/publish", headers=headers1, json={
        "topic": "action.completed",
        "action": "customer_research",
        "description": "Completed initial research on Customer 42",
        "entity_id": customer_id,
        "entity_type": "customer",
        "data": {
            "findings": ["High value customer", "Interested in premium tier", "Previous engagement: 3 months ago"],
            "confidence": 0.85
        }
    }).json()
    print("[ResearchAgent] Published: customer_research")
    print(f"   → Recipients: {pub1['recipient_count']} agents")
    
    time.sleep(0.5)
    
    # Agent 2 tries to also work on the customer (should be blocked)
    claim2 = requests.post(f"{BASE_URL}/share/claim/{customer_id}", headers=headers2)
    if claim2.status_code == 409:
        print(f"\n[AnalysisAgent] ⚠️ Cannot claim {customer_id} - already claimed!")
        print("   → Will coordinate with ResearchAgent instead")
    
    # Agent 2 publishes analysis request (using action.started as topic)
    resp = requests.post(f"{BASE_URL}/share/publish", headers=headers2, json={
        "topic": "action.started",
        "action": "analysis_request",
        "description": "Requesting deeper analysis on Customer 42 research",
        "entity_id": customer_id,
        "target_agent_ids": [agent1["id"]],  # Direct message to Agent 1
        "data": {
            "request": "Please provide revenue history and engagement metrics"
        },
        "priority": 5
    })
    if resp.status_code == 200:
        print("\n[AnalysisAgent] Published: analysis_request (direct to ResearchAgent)")
    else:
        print(f"\n[AnalysisAgent] Failed: {resp.status_code} - {resp.text[:100]}")
    
    time.sleep(0.5)
    
    # Agent 1 responds with more data
    resp = requests.post(f"{BASE_URL}/share/publish", headers=headers1, json={
        "topic": "action.completed",
        "action": "extended_research",
        "description": "Completed extended research with revenue data",
        "entity_id": customer_id,
        "data": {
            "revenue_history": [10000, 15000, 12000, 18000],
            "engagement_score": 0.72,
            "recommendation": "Offer premium upgrade with 15% discount"
        }
    })
    if resp.status_code == 200:
        print("\n[ResearchAgent] Published: extended_research")
    
    # Agent 1 makes a decision
    resp = requests.post(f"{BASE_URL}/share/publish", headers=headers1, json={
        "topic": "decision.made",
        "action": "strategy_decision",
        "description": "Decided on outreach strategy for Customer 42",
        "entity_id": customer_id,
        "data": {
            "decision": "Premium upgrade offer",
            "rationale": "High engagement + revenue growth trend",
            "next_steps": ["Send personalized email", "Schedule follow-up call"]
        },
        "priority": 8
    })
    if resp.status_code == 200:
        print("[ResearchAgent] Published: strategy_decision (priority: 8)")
    
    # Release the claim
    requests.post(f"{BASE_URL}/share/release/{customer_id}", headers=headers1)
    print(f"\n[ResearchAgent] Released claim on {customer_id}")
    
    # Query shared context
    print("\n" + "-" * 40)
    print("\n🔍 Querying shared context...")
    
    query = requests.get(f"{BASE_URL}/share/query?q=customer").json()
    print("\nQuery: 'customer'")
    print(f"   Found: {query['count']} events")
    
    # Get recent events
    events = requests.get(f"{BASE_URL}/share/events?limit=5").json()
    print("\n📜 Recent shared events:")
    for e in events["events"][:5]:
        print(f"   • [{e['topic']}] {e['action']}: {e['description'][:40]}...")
    
    # Disconnect
    print("\n🔌 Disconnecting agents...")
    requests.post(f"{BASE_URL}/share/disconnect", headers=headers1)
    requests.post(f"{BASE_URL}/share/disconnect", headers=headers2)
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)
    print("\nThis demonstrated:")
    print("  • Two agents connecting to the sharing hub")
    print("  • Topic-based event subscriptions")
    print("  • Publishing context updates")
    print("  • Conflict prevention with entity claims")
    print("  • Direct messaging between agents")
    print("  • Querying shared context history")


if __name__ == "__main__":
    main()
