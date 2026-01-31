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
    
    def status(self):
        """Check server status."""
        try:
            self._request("GET", "/health")
            print(f"✅ AgentGraph server is healthy at {self.base_url}")
            
            # Get agent count
            agents = self._request("GET", "/agents")
            print(f"   Agents: {len(agents.get('agents', []))}")
            print("   Status: Running")
            
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


if __name__ == "__main__":
    main()
