#!/usr/bin/env python3
"""
AgentGraph CLI

Command-line interface for interacting with AgentGraph.

Usage:
    agentgraph query "what did I work on today?"
    agentgraph events --limit 20
    agentgraph entities
    agentgraph log tool.call "search" --description "Searched for X"
    agentgraph status
"""

import argparse
import json
import os
import sys

import requests


class AgentGraphCLI:
    """CLI client for AgentGraph."""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or os.environ.get("AGENTGRAPH_URL", "http://localhost:8080")).rstrip("/")
        self.api_key = api_key or os.environ.get("AGENTGRAPH_API_KEY", "")
    
    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def _request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self._headers(), timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to AgentGraph at {self.base_url}", file=sys.stderr)
            print("   Is the server running? Start it with: python -m agentgraph.api.server", file=sys.stderr)
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"❌ API error: {e.response.status_code} {e.response.text}", file=sys.stderr)
            sys.exit(1)
    
    def query(self, question: str, json_output: bool = False):
        """Ask a natural language question."""
        result = self._request("POST", "/query", json={"question": question})
        
        if json_output:
            print(json.dumps(result, indent=2, default=str))
            return
        
        if result.get("answer"):
            print(f"\n📝 {result['answer']}\n")
        
        events = result.get("events", [])
        if events:
            print(f"📊 Matching Events ({len(events)}):")
            for event in events[:15]:
                ts = event.get("timestamp", "")[:16].replace("T", " ")
                status = "✓" if event.get("status") == "success" else "✗" if event.get("status") == "error" else "○"
                print(f"  {status} [{ts}] {event.get('type', '')} | {event.get('action', '')}")
                if event.get("description"):
                    print(f"      {event.get('description', '')[:80]}")
            if len(events) > 15:
                print(f"  ... and {len(events) - 15} more")
        
        entities = result.get("entities", [])
        if entities:
            print(f"\n🔗 Related Entities ({len(entities)}):")
            for entity in entities[:10]:
                print(f"  • [{entity.get('type', '')}] {entity.get('name', '')}")
    
    def events(self, limit: int = 20, event_type: str = None, json_output: bool = False):
        """List recent events."""
        url = f"/events?limit={limit}"
        if event_type:
            url += f"&type={event_type}"
        
        result = self._request("GET", url)
        events = result.get("events", [])
        
        if json_output:
            print(json.dumps(events, indent=2, default=str))
            return
        
        if not events:
            print("No events found.")
            return
        
        print(f"\n📊 Recent Events ({len(events)}):\n")
        for event in events:
            ts = event.get("timestamp", "")[:16].replace("T", " ")
            status = "✓" if event.get("status") == "success" else "✗" if event.get("status") == "error" else "○"
            print(f"{status} [{ts}] {event.get('type', ''):<16} | {event.get('action', '')}")
            if event.get("description"):
                print(f"   {event.get('description', '')[:90]}")
    
    def entities(self, entity_type: str = None, json_output: bool = False):
        """List entities."""
        url = "/entities"
        if entity_type:
            url += f"?type={entity_type}"
        
        result = self._request("GET", url)
        entities = result.get("entities", [])
        
        if json_output:
            print(json.dumps(entities, indent=2, default=str))
            return
        
        if not entities:
            print("No entities found.")
            return
        
        print(f"\n🔗 Entities ({len(entities)}):\n")
        for entity in entities:
            print(f"• [{entity.get('type', ''):<10}] {entity.get('name', '')}")
            if entity.get("metadata"):
                print(f"   {json.dumps(entity.get('metadata', {}))[:80]}")
    
    def log(self, event_type: str, action: str, description: str = "", 
            input_data: str = None, tags: str = None, status: str = "success"):
        """Log an event."""
        payload = {
            "type": event_type,
            "action": action,
            "description": description,
            "status": status,
            "tags": [t.strip() for t in tags.split(",")] if tags else []
        }
        
        if input_data:
            try:
                payload["input_data"] = json.loads(input_data)
            except json.JSONDecodeError:
                payload["input_data"] = {"raw": input_data}
        
        result = self._request("POST", "/events", json=payload)
        print(f"✓ Logged event: {result.get('id', 'unknown')}")
    
    def search(self, query: str, semantic: bool = False, limit: int = 20, json_output: bool = False):
        """Search events."""
        if semantic:
            result = self._request("GET", f"/search/semantic?q={query}&limit={limit}")
            items = result.get("results", [])
        else:
            result = self._request("GET", f"/search/events?q={query}&limit={limit}")
            items = result.get("events", [])
        
        if json_output:
            print(json.dumps(items, indent=2, default=str))
            return
        
        if not items:
            print("No results found.")
            return
        
        print(f"\n🔍 Search Results ({len(items)}):\n")
        for item in items:
            if semantic:
                event = item.get("event", {})
                score = item.get("similarity", 0)
                ts = event.get("timestamp", "")[:16].replace("T", " ")
                print(f"[{score:.2f}] [{ts}] {event.get('type', '')} | {event.get('action', '')}")
            else:
                ts = item.get("timestamp", "")[:16].replace("T", " ")
                print(f"[{ts}] {item.get('type', '')} | {item.get('action', '')}")
            
            desc = (item.get("event", {}) if semantic else item).get("description", "")
            if desc:
                print(f"   {desc[:90]}")
    
    def graph(self, json_output: bool = False):
        """Get graph data."""
        result = self._request("GET", "/graph/data")
        
        if json_output:
            print(json.dumps(result, indent=2, default=str))
            return
        
        nodes = result.get("nodes", [])
        links = result.get("links", [])
        
        print(f"\n🕸️ Knowledge Graph: {len(nodes)} nodes, {len(links)} relationships\n")
        
        if nodes:
            print("Nodes:")
            for node in nodes[:20]:
                print(f"  • [{node.get('type', '')}] {node.get('name', '')} ({node.get('id', '')[:8]}...)")
        
        if links:
            print("\nRelationships:")
            for link in links[:20]:
                print(f"  → {link.get('source', '')[:8]}... --[{link.get('type', '')}]--> {link.get('target', '')[:8]}...")
    
    # ==================== Registry Commands ====================
    
    def registry_list(self, online_only: bool = False, json_output: bool = False):
        """List registered agents."""
        params = {}
        if online_only:
            params["online_only"] = "true"
        
        result = self._request("GET", "/registry/agents", params=params)
        
        if json_output:
            print(json.dumps(result, indent=2, default=str))
            return
        
        if not result:
            print("📋 No agents registered yet")
            return
        
        print(f"\n🤖 Registered Agents ({len(result)} total)\n")
        
        for agent in result:
            status_icon = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(agent["status"], "⚪")
            caps = ", ".join([c["name"] for c in agent.get("capabilities", [])])
            print(f"  {status_icon} {agent['name']} ({agent['id'][:8]}...)")
            if agent.get("description"):
                print(f"      {agent['description']}")
            if caps:
                print(f"      Capabilities: {caps}")
            print()
    
    def registry_register(
        self, 
        name: str, 
        capabilities: list = None,
        description: str = "",
        endpoint: str = None,
        json_output: bool = False
    ):
        """Register a new agent."""
        caps = []
        for cap in (capabilities or []):
            if isinstance(cap, str):
                caps.append({"name": cap, "metadata": {}})
        
        data = {
            "name": name,
            "description": description,
            "capabilities": caps,
            "endpoint": endpoint,
        }
        
        result = self._request("POST", "/registry/agents", json=data)
        
        if json_output:
            print(json.dumps(result, indent=2, default=str))
            return
        
        print(f"✅ Agent registered: {result['name']} (ID: {result['id'][:8]}...)")
        if caps:
            print(f"   Capabilities: {', '.join(c['name'] for c in caps)}")
    
    def registry_discover(
        self, 
        capability: str = None,
        online_only: bool = True,
        json_output: bool = False
    ):
        """Discover agents by capability."""
        params = {"online_only": str(online_only).lower()}
        if capability:
            params["capability"] = capability
        
        result = self._request("GET", "/registry/agents", params=params)
        
        if json_output:
            print(json.dumps(result, indent=2, default=str))
            return
        
        if not result:
            msg = f"No agents found"
            if capability:
                msg += f" with capability '{capability}'"
            print(f"📋 {msg}")
            return
        
        cap_msg = f" with '{capability}'" if capability else ""
        print(f"\n🔍 Found {len(result)} agent(s){cap_msg}\n")
        
        for agent in result:
            status_icon = {"online": "🟢", "busy": "🟡", "offline": "🔴"}.get(agent["status"], "⚪")
            print(f"  {status_icon} {agent['name']} ({agent['id'][:8]}...)")
            if agent.get("endpoint"):
                print(f"      Endpoint: {agent['endpoint']}")
    
    def registry_heartbeat(self, agent_id: str):
        """Send heartbeat for an agent."""
        result = self._request("POST", f"/registry/agents/{agent_id}/heartbeat")
        print(f"💓 Heartbeat sent for agent {agent_id[:8]}...")
    
    def registry_stats(self, json_output: bool = False):
        """Get registry statistics."""
        result = self._request("GET", "/registry/stats")
        
        if json_output:
            print(json.dumps(result, indent=2, default=str))
            return
        
        print(f"\n📊 Registry Stats")
        print(f"   Total Agents: {result['total_agents']}")
        print(f"   Online: {result['online_agents']}")
        print(f"   Offline: {result['offline_agents']}")
    
    def status(self):
        """Check server status."""
        try:
            self._request("GET", "/health")
            print(f"✅ AgentGraph server is healthy at {self.base_url}")
            
            # Get agent count
            agents = self._request("GET", "/agents")
            print(f"   Agents: {len(agents.get('agents', []))}")
            print("   Status: Running")
            
            # Registry stats
            try:
                registry_stats = self._request("GET", "/registry/stats")
                print(f"   Registry: {registry_stats['total_agents']} agents ({registry_stats['online_agents']} online)")
            except Exception:
                pass
            
        except Exception as e:
            print(f"❌ AgentGraph server unavailable: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="AgentGraph CLI - Track, visualize, and query AI agent activities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    agentgraph status                           # Check server status
    agentgraph query "what did I work on?"      # Natural language query
    agentgraph events --limit 50                # List recent events
    agentgraph entities --type task             # List entities by type
    agentgraph search "error" --semantic        # Semantic search
    agentgraph log tool.call search             # Log an event
    agentgraph graph                            # Show knowledge graph

Environment Variables:
    AGENTGRAPH_URL      API server URL (default: http://localhost:8080)
    AGENTGRAPH_API_KEY  API key for authentication
"""
    )
    
    parser.add_argument("--url", help="AgentGraph server URL")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status
    subparsers.add_parser("status", help="Check server status")
    
    # Query
    query_parser = subparsers.add_parser("query", help="Natural language query")
    query_parser.add_argument("question", help="Question to ask")
    
    # Events
    events_parser = subparsers.add_parser("events", help="List recent events")
    events_parser.add_argument("--limit", type=int, default=20, help="Number of events")
    events_parser.add_argument("--type", dest="event_type", help="Filter by event type")
    
    # Entities
    entities_parser = subparsers.add_parser("entities", help="List entities")
    entities_parser.add_argument("--type", dest="entity_type", help="Filter by entity type")
    
    # Search
    search_parser = subparsers.add_parser("search", help="Search events")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--semantic", action="store_true", help="Use semantic search")
    search_parser.add_argument("--limit", type=int, default=20, help="Number of results")
    
    # Log
    log_parser = subparsers.add_parser("log", help="Log an event")
    log_parser.add_argument("event_type", help="Event type (e.g., tool.call, decision)")
    log_parser.add_argument("action", help="Action name")
    log_parser.add_argument("--description", "-d", default="", help="Description")
    log_parser.add_argument("--input", dest="input_data", help="Input data (JSON)")
    log_parser.add_argument("--tags", help="Comma-separated tags")
    log_parser.add_argument("--status", default="success", help="Status (success/error/pending)")
    
    # Graph
    subparsers.add_parser("graph", help="Show knowledge graph")
    
    # Registry - Agent Discovery
    registry_parser = subparsers.add_parser("registry", help="Agent registry commands")
    registry_subparsers = registry_parser.add_subparsers(dest="registry_command", help="Registry commands")
    
    # registry list
    registry_list_parser = registry_subparsers.add_parser("list", help="List registered agents")
    registry_list_parser.add_argument("--online", action="store_true", help="Only show online agents")
    
    # registry register
    registry_register_parser = registry_subparsers.add_parser("register", help="Register a new agent")
    registry_register_parser.add_argument("name", help="Agent name")
    registry_register_parser.add_argument("--capabilities", "-c", nargs="*", help="Capabilities")
    registry_register_parser.add_argument("--description", "-d", default="", help="Description")
    registry_register_parser.add_argument("--endpoint", "-e", help="Endpoint URL")
    
    # registry discover
    registry_discover_parser = registry_subparsers.add_parser("discover", help="Find agents by capability")
    registry_discover_parser.add_argument("capability", nargs="?", help="Capability to search for")
    registry_discover_parser.add_argument("--offline", action="store_true", help="Include offline agents")
    
    # registry heartbeat
    registry_heartbeat_parser = registry_subparsers.add_parser("heartbeat", help="Send heartbeat")
    registry_heartbeat_parser.add_argument("agent_id", help="Agent ID")
    
    # registry stats
    registry_subparsers.add_parser("stats", help="Registry statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = AgentGraphCLI(base_url=args.url, api_key=args.api_key)
    
    if args.command == "status":
        cli.status()
    elif args.command == "query":
        cli.query(args.question, json_output=args.json)
    elif args.command == "events":
        cli.events(limit=args.limit, event_type=args.event_type, json_output=args.json)
    elif args.command == "entities":
        cli.entities(entity_type=args.entity_type, json_output=args.json)
    elif args.command == "search":
        cli.search(args.query, semantic=args.semantic, limit=args.limit, json_output=args.json)
    elif args.command == "log":
        cli.log(args.event_type, args.action, args.description, args.input_data, args.tags, args.status)
    elif args.command == "graph":
        cli.graph(json_output=args.json)
    elif args.command == "registry":
        if not args.registry_command:
            registry_parser.print_help()
            sys.exit(1)
        elif args.registry_command == "list":
            cli.registry_list(online_only=args.online, json_output=args.json)
        elif args.registry_command == "register":
            cli.registry_register(
                args.name, 
                capabilities=args.capabilities,
                description=args.description,
                endpoint=args.endpoint,
                json_output=args.json
            )
        elif args.registry_command == "discover":
            cli.registry_discover(
                capability=args.capability,
                online_only=not args.offline,
                json_output=args.json
            )
        elif args.registry_command == "heartbeat":
            cli.registry_heartbeat(args.agent_id)
        elif args.registry_command == "stats":
            cli.registry_stats(json_output=args.json)


if __name__ == "__main__":
    main()
