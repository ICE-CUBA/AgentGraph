# MCP Integration

AgentGraph provides an MCP (Model Context Protocol) server for integration with AI coding tools like Claude Code, Cursor, Cline, and Windsurf.

## Quick Setup

### Claude Code

```bash
claude mcp add agentgraph -- python -m agentgraph.mcp
```

### Manual Configuration

Add to your MCP config:

```json
{
  "mcpServers": {
    "agentgraph": {
      "command": "python",
      "args": ["-m", "agentgraph.mcp"]
    }
  }
}
```

### HTTP Transport

Run as HTTP server:

```bash
python -m agentgraph.mcp --transport http --port 8081
```

---

## Available Tools

### query_agentgraph

Ask natural language questions about agent activity.

```
Input: {"question": "what did my agent work on today?"}
Output: {"answer": "...", "events": [...]}
```

### log_event

Log an event.

```
Input: {
  "description": "Searched for papers",
  "event_type": "tool.call",
  "action": "search"
}
```

### search_events

Search events by keyword.

```
Input: {"query": "error", "limit": 10}
Output: {"events": [...]}
```

### semantic_search

Search using natural language (requires embeddings).

```
Input: {"query": "customer onboarding issues", "limit": 5}
Output: {"results": [...]}
```

### create_entity

Create an entity in the knowledge graph.

```
Input: {
  "name": "Acme Corp",
  "entity_type": "user",
  "metadata": {"industry": "tech"}
}
```

### create_relationship

Link two entities.

```
Input: {
  "source_id": "...",
  "target_id": "...",
  "relationship_type": "owns"
}
```

### get_graph_data

Get the knowledge graph for visualization.

```
Output: {"nodes": [...], "links": [...]}
```

### get_stats

Get agent statistics.

```
Output: {"total_events": 150, "entities": 25, ...}
```

---

## Resources

The MCP server also exposes resources:

| URI | Description |
|-----|-------------|
| `agentgraph://events/recent` | Recent events |
| `agentgraph://entities` | All entities |
| `agentgraph://graph` | Knowledge graph data |
| `agentgraph://stats` | Statistics |

---

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENTGRAPH_URL` | Server URL | `http://localhost:8080` |
| `AGENTGRAPH_API_KEY` | API key | None |
| `AGENTGRAPH_MCP_PORT` | HTTP port | 8081 |

---

## Example Usage in Claude

Once configured, you can use AgentGraph directly in conversations:

```
Human: What did my agent work on today?

Claude: [Uses query_agentgraph tool]
Based on the logs, your agent:
- Processed 15 customer requests
- Made 3 API calls to external services
- Created 2 new entities in the knowledge graph
```
