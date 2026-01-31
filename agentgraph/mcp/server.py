"""
AgentGraph MCP Server

Exposes AgentGraph functionality via Model Context Protocol for integration
with AI coding tools (Claude Code, Cursor, Cline, Windsurf, etc.)

Usage:
    # Stdio transport (for Claude Desktop, Cursor, etc.)
    python -m agentgraph.mcp
    
    # HTTP transport
    python -m agentgraph.mcp --transport http --port 8081
    
    # With custom AgentGraph server
    python -m agentgraph.mcp --agentgraph-url http://localhost:8080 --api-key YOUR_KEY
"""

import os
import json
from typing import Any, Dict, List, Optional

try:
    from mcp.server.mcpserver import MCPServer
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPServer = None

import requests


class AgentGraphMCPClient:
    """Internal client for the MCP server to communicate with AgentGraph API."""
    
    def __init__(self, base_url: str = "http://localhost:8080", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("AGENTGRAPH_API_KEY", "")
    
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self._headers(), timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return {"error": f"Cannot connect to AgentGraph at {self.base_url}. Is the server running?"}
        except Exception as e:
            return {"error": str(e)}
    
    def log_event(self, event_type: str, action: str, description: str = "", 
                  input_data: Optional[Dict] = None, output_data: Optional[Dict] = None,
                  tags: Optional[List[str]] = None, status: str = "success") -> Dict:
        return self._request("POST", "/events", json={
            "type": event_type,
            "action": action,
            "description": description,
            "input_data": input_data or {},
            "output_data": output_data or {},
            "tags": tags or [],
            "status": status
        })
    
    def query(self, question: str) -> Dict:
        return self._request("POST", "/query", json={"question": question})
    
    def search_events(self, query: str, limit: int = 20) -> Dict:
        return self._request("GET", f"/search/events?q={query}&limit={limit}")
    
    def search_semantic(self, query: str, limit: int = 10) -> Dict:
        return self._request("GET", f"/search/semantic?q={query}&limit={limit}")
    
    def get_events(self, limit: int = 50, event_type: Optional[str] = None) -> Dict:
        url = f"/events?limit={limit}"
        if event_type:
            url += f"&type={event_type}"
        return self._request("GET", url)
    
    def get_entities(self, entity_type: Optional[str] = None) -> Dict:
        url = "/entities"
        if entity_type:
            url += f"?type={entity_type}"
        return self._request("GET", url)
    
    def get_entity(self, entity_id: str) -> Dict:
        return self._request("GET", f"/entities/{entity_id}")
    
    def create_entity(self, entity_type: str, name: str, metadata: Optional[Dict] = None) -> Dict:
        return self._request("POST", "/entities", json={
            "type": entity_type,
            "name": name,
            "metadata": metadata or {}
        })
    
    def create_relationship(self, source_id: str, target_id: str, rel_type: str, 
                           metadata: Optional[Dict] = None) -> Dict:
        return self._request("POST", "/relationships", json={
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "type": rel_type,
            "metadata": metadata or {}
        })
    
    def get_graph(self) -> Dict:
        return self._request("GET", "/graph/data")
    
    def get_agent_stats(self) -> Dict:
        # Get agents and their stats
        agents = self._request("GET", "/agents")
        if "error" in agents:
            return agents
        
        stats = []
        for agent in agents.get("agents", []):
            agent_stats = self._request("GET", f"/agents/{agent['id']}/stats")
            stats.append({
                "agent": agent,
                "stats": agent_stats
            })
        return {"agent_stats": stats}
    
    def health_check(self) -> Dict:
        return self._request("GET", "/health")


def create_mcp_server(
    agentgraph_url: str = "http://localhost:8080",
    api_key: Optional[str] = None
) -> "MCPServer":
    """
    Create an MCP server for AgentGraph.
    
    Args:
        agentgraph_url: URL of the AgentGraph API server
        api_key: API key for authentication
    
    Returns:
        Configured MCPServer instance
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP SDK not installed. Install with: pip install mcp[cli] or pip install agentgraph[mcp]"
        )
    
    client = AgentGraphMCPClient(base_url=agentgraph_url, api_key=api_key)
    mcp = MCPServer("AgentGraph")
    
    # ==================== TOOLS ====================
    
    @mcp.tool()
    def log_event(
        event_type: str,
        action: str,
        description: str = "",
        input_data: Optional[str] = None,
        output_data: Optional[str] = None,
        tags: Optional[str] = None,
        status: str = "success"
    ) -> str:
        """
        Log an event to AgentGraph for tracking agent activities.
        
        Args:
            event_type: Type of event (action.complete, tool.call, decision, reasoning, message.sent, etc.)
            action: Name of the action being logged
            description: Human-readable description of what happened
            input_data: JSON string of input parameters (optional)
            output_data: JSON string of output/result (optional)
            tags: Comma-separated tags for categorization (optional)
            status: Event status (success, error, pending)
        
        Returns:
            Event ID or error message
        """
        try:
            parsed_input = json.loads(input_data) if input_data else None
            parsed_output = json.loads(output_data) if output_data else None
            parsed_tags = [t.strip() for t in tags.split(",")] if tags else None
        except json.JSONDecodeError as e:
            return f"Error parsing JSON: {e}"
        
        result = client.log_event(
            event_type=event_type,
            action=action,
            description=description,
            input_data=parsed_input,
            output_data=parsed_output,
            tags=parsed_tags,
            status=status
        )
        
        if "error" in result:
            return f"Error: {result['error']}"
        return f"Logged event: {result.get('id', 'unknown')}"
    
    @mcp.tool()
    def query_agentgraph(question: str) -> str:
        """
        Ask a natural language question about agent activities.
        
        Use this to find out what happened, what tools were used, what decisions
        were made, and more. The query engine will search through events, entities,
        and relationships to answer your question.
        
        Args:
            question: Natural language question (e.g., "What did I work on today?",
                     "What tools have been used?", "Show me recent errors")
        
        Returns:
            Answer with relevant events and entities
        """
        result = client.query(question)
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        # Format response nicely
        output = []
        
        if result.get("answer"):
            output.append(f"Answer: {result['answer']}")
        
        if result.get("events"):
            output.append(f"\nMatching Events ({len(result['events'])}):")
            for event in result["events"][:10]:
                ts = event.get("timestamp", "")[:19]
                output.append(f"  - [{ts}] {event.get('type', '')} | {event.get('action', '')} | {event.get('description', '')[:60]}")
        
        if result.get("entities"):
            output.append(f"\nRelated Entities ({len(result['entities'])}):")
            for entity in result["entities"][:10]:
                output.append(f"  - [{entity.get('type', '')}] {entity.get('name', '')}")
        
        return "\n".join(output) if output else "No results found."
    
    @mcp.tool()
    def search_events(query: str, limit: int = 20) -> str:
        """
        Search for events by keyword.
        
        Args:
            query: Search query (searches action, description, and metadata)
            limit: Maximum number of results (default 20)
        
        Returns:
            List of matching events
        """
        result = client.search_events(query, limit)
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        events = result.get("events", [])
        if not events:
            return "No events found matching your query."
        
        output = [f"Found {len(events)} events:\n"]
        for event in events:
            ts = event.get("timestamp", "")[:19]
            output.append(f"- [{ts}] {event.get('type', '')} | {event.get('action', '')} | {event.get('description', '')[:80]}")
        
        return "\n".join(output)
    
    @mcp.tool()
    def semantic_search(query: str, limit: int = 10) -> str:
        """
        Semantic search using embeddings for more intelligent matching.
        
        Finds events that are semantically similar to your query, even if they
        don't contain the exact keywords.
        
        Args:
            query: Natural language query
            limit: Maximum number of results
        
        Returns:
            Semantically similar events with similarity scores
        """
        result = client.search_semantic(query, limit)
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        events = result.get("results", [])
        if not events:
            return "No semantically similar events found."
        
        output = [f"Found {len(events)} semantically similar events:\n"]
        for item in events:
            event = item.get("event", {})
            score = item.get("similarity", 0)
            ts = event.get("timestamp", "")[:19]
            output.append(f"- [{score:.2f}] [{ts}] {event.get('type', '')} | {event.get('action', '')}")
            if event.get("description"):
                output.append(f"    {event.get('description', '')[:100]}")
        
        return "\n".join(output)
    
    @mcp.tool()
    def get_recent_events(limit: int = 20, event_type: Optional[str] = None) -> str:
        """
        Get recent events from AgentGraph.
        
        Args:
            limit: Number of events to retrieve (default 20)
            event_type: Filter by event type (optional, e.g., "tool.call", "decision")
        
        Returns:
            List of recent events
        """
        result = client.get_events(limit, event_type)
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        events = result.get("events", [])
        if not events:
            return "No events found."
        
        output = [f"Recent events ({len(events)}):\n"]
        for event in events:
            ts = event.get("timestamp", "")[:19]
            status = "✓" if event.get("status") == "success" else "✗" if event.get("status") == "error" else "○"
            output.append(f"{status} [{ts}] {event.get('type', '')} | {event.get('action', '')}")
            if event.get("description"):
                output.append(f"   {event.get('description', '')[:100]}")
        
        return "\n".join(output)
    
    @mcp.tool()
    def create_entity(entity_type: str, name: str, metadata: Optional[str] = None) -> str:
        """
        Create an entity in the knowledge graph.
        
        Entities represent things like users, tasks, documents, tools, or any
        custom objects you want to track relationships between.
        
        Args:
            entity_type: Type of entity (user, task, document, tool, resource, custom)
            name: Name of the entity
            metadata: Optional JSON string with additional metadata
        
        Returns:
            Entity ID or error message
        """
        try:
            parsed_metadata = json.loads(metadata) if metadata else None
        except json.JSONDecodeError as e:
            return f"Error parsing metadata JSON: {e}"
        
        result = client.create_entity(entity_type, name, parsed_metadata)
        
        if "error" in result:
            return f"Error: {result['error']}"
        return f"Created entity: {result.get('id', 'unknown')} (type: {entity_type}, name: {name})"
    
    @mcp.tool()
    def create_relationship(source_id: str, target_id: str, relationship_type: str, 
                           metadata: Optional[str] = None) -> str:
        """
        Create a relationship between two entities in the knowledge graph.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            relationship_type: Type of relationship (created, modified, referenced, 
                              depends_on, caused, responded_to, part_of, owns, 
                              delegated_to, collaborated_with)
            metadata: Optional JSON string with additional metadata
        
        Returns:
            Relationship ID or error message
        """
        try:
            parsed_metadata = json.loads(metadata) if metadata else None
        except json.JSONDecodeError as e:
            return f"Error parsing metadata JSON: {e}"
        
        result = client.create_relationship(source_id, target_id, relationship_type, parsed_metadata)
        
        if "error" in result:
            return f"Error: {result['error']}"
        return f"Created relationship: {source_id} --[{relationship_type}]--> {target_id}"
    
    @mcp.tool()
    def get_graph_data() -> str:
        """
        Get the full entity-relationship graph data.
        
        Returns nodes (entities) and links (relationships) suitable for visualization.
        
        Returns:
            Graph data with nodes and links
        """
        result = client.get_graph()
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        nodes = result.get("nodes", [])
        links = result.get("links", [])
        
        output = [f"Graph has {len(nodes)} nodes and {len(links)} links\n"]
        
        if nodes:
            output.append("Nodes:")
            for node in nodes[:20]:
                output.append(f"  - [{node.get('type', '')}] {node.get('name', '')} (id: {node.get('id', '')[:8]}...)")
        
        if links:
            output.append("\nRelationships:")
            for link in links[:20]:
                output.append(f"  - {link.get('source', '')[:8]}... --[{link.get('type', '')}]--> {link.get('target', '')[:8]}...")
        
        if len(nodes) > 20 or len(links) > 20:
            output.append(f"\n(Showing first 20 of each, {len(nodes)} nodes and {len(links)} links total)")
        
        return "\n".join(output)
    
    @mcp.tool()
    def get_agent_stats() -> str:
        """
        Get statistics for all registered agents.
        
        Shows event counts, activity summaries, and performance metrics for each agent.
        
        Returns:
            Agent statistics
        """
        result = client.get_agent_stats()
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        stats = result.get("agent_stats", [])
        if not stats:
            return "No agents registered yet."
        
        output = [f"Stats for {len(stats)} agent(s):\n"]
        for item in stats:
            agent = item.get("agent", {})
            agent_stats = item.get("stats", {})
            output.append(f"Agent: {agent.get('name', 'Unknown')} ({agent.get('platform', '')})")
            output.append(f"  Events: {agent_stats.get('event_count', 0)}")
            output.append(f"  Sessions: {agent_stats.get('session_count', 0)}")
            if agent_stats.get("last_event_at"):
                output.append(f"  Last active: {agent_stats.get('last_event_at', '')[:19]}")
            output.append("")
        
        return "\n".join(output)
    
    @mcp.tool()
    def health_check() -> str:
        """
        Check if the AgentGraph server is running and healthy.
        
        Returns:
            Server health status
        """
        result = client.health_check()
        
        if "error" in result:
            return f"❌ AgentGraph server unavailable: {result['error']}"
        
        return f"✅ AgentGraph server is healthy at {agentgraph_url}"
    
    # ==================== RESOURCES ====================
    
    @mcp.resource("agentgraph://events/recent")
    def get_recent_events_resource() -> str:
        """Get the most recent events from AgentGraph."""
        result = client.get_events(limit=30)
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2, default=str)
    
    @mcp.resource("agentgraph://entities")
    def get_entities_resource() -> str:
        """Get all entities in the knowledge graph."""
        result = client.get_entities()
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2, default=str)
    
    @mcp.resource("agentgraph://graph")
    def get_graph_resource() -> str:
        """Get the full entity-relationship graph."""
        result = client.get_graph()
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2, default=str)
    
    @mcp.resource("agentgraph://stats")
    def get_stats_resource() -> str:
        """Get agent statistics."""
        result = client.get_agent_stats()
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2, default=str)
    
    return mcp


def run_mcp_server(
    transport: str = "stdio",
    port: int = 8081,
    agentgraph_url: str = "http://localhost:8080",
    api_key: Optional[str] = None
):
    """
    Run the AgentGraph MCP server.
    
    Args:
        transport: Transport type ("stdio" or "streamable-http")
        port: Port for HTTP transport
        agentgraph_url: AgentGraph API URL
        api_key: API key for authentication
    """
    mcp = create_mcp_server(agentgraph_url=agentgraph_url, api_key=api_key)
    
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport in ("http", "streamable-http"):
        mcp.run(transport="streamable-http", port=port)
    else:
        raise ValueError(f"Unknown transport: {transport}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentGraph MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport type (default: stdio)")
    parser.add_argument("--port", type=int, default=8081,
                       help="Port for HTTP transport (default: 8081)")
    parser.add_argument("--agentgraph-url", default="http://localhost:8080",
                       help="AgentGraph API URL (default: http://localhost:8080)")
    parser.add_argument("--api-key", default=None,
                       help="API key for AgentGraph authentication")
    
    args = parser.parse_args()
    
    run_mcp_server(
        transport=args.transport,
        port=args.port,
        agentgraph_url=args.agentgraph_url,
        api_key=args.api_key
    )
