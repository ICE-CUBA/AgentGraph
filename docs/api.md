# AgentGraph API Reference

## Base URL

```
http://localhost:8080
```

## Authentication

Most endpoints require an API key passed in the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8080/events
```

---

## Core Endpoints

### Health Check

```
GET /health
```

Returns server status.

### Events

```
POST /events
```

Log an event.

**Body:**
```json
{
  "type": "tool.call",
  "action": "search",
  "description": "Searched for papers",
  "input_data": {"query": "AI research"},
  "output_data": {"count": 10},
  "tags": ["research"]
}
```

```
GET /events
```

List events with optional filters.

**Query params:**
- `agent_id` - Filter by agent
- `session_id` - Filter by session
- `event_type` - Filter by type
- `limit` - Max results (default 100)
- `offset` - Pagination offset

### Entities

```
POST /entities
```

Create an entity in the knowledge graph.

**Body:**
```json
{
  "type": "user",
  "name": "Acme Corp",
  "metadata": {"industry": "tech"}
}
```

```
GET /entities/{entity_id}
```

Get entity details.

### Relationships

```
POST /relationships
```

Create a relationship between entities.

**Body:**
```json
{
  "source_entity_id": "...",
  "target_entity_id": "...",
  "type": "owns",
  "metadata": {}
}
```

### Query

```
POST /query
```

Natural language query.

**Body:**
```json
{
  "question": "what did my agent do today?"
}
```

---

## Registry Endpoints

### Agents

```
POST /registry/agents
```

Register an agent.

**Body:**
```json
{
  "name": "TranslatorBot",
  "description": "Translates text",
  "capabilities": [
    {"name": "translate", "metadata": {"languages": ["en", "es"]}}
  ],
  "endpoint": "http://..."
}
```

```
GET /registry/agents
```

Discover agents.

**Query params:**
- `capability` - Filter by capability
- `online_only` - Only return online agents

```
GET /registry/agents/{agent_id}
```

Get agent details.

```
POST /registry/agents/{agent_id}/heartbeat
```

Send heartbeat (keeps agent marked online).

```
PATCH /registry/agents/{agent_id}/status
```

Update agent status.

**Body:**
```json
{
  "status": "busy"
}
```

### Stats

```
GET /registry/stats
```

Get registry statistics.

---

## Reputation Endpoints

### Tasks

```
POST /registry/tasks/start
```

Record task start.

**Body:**
```json
{
  "agent_id": "...",
  "task_type": "translate"
}
```

```
POST /registry/tasks/{task_id}/complete
```

Record task completion.

**Body:**
```json
{
  "outcome": "success"
}
```

```
POST /registry/tasks/{task_id}/rate
```

Rate a task.

**Body:**
```json
{
  "rating": 0.9,
  "rated_by": "agent-id"
}
```

### Trust

```
GET /registry/agents/{agent_id}/trust
```

Get agent trust score.

```
GET /registry/agents/{agent_id}/reputation
```

Get detailed reputation stats.

```
GET /registry/leaderboard
```

Get top agents by trust score.

---

## Sharing Endpoints

```
POST /share/connect
```

Connect agent to sharing hub.

```
POST /share/subscribe
```

Subscribe to events.

```
POST /share/publish
```

Publish an event.

```
POST /share/claim/{entity_id}
```

Claim exclusive work on an entity.

```
POST /share/release/{entity_id}
```

Release a claim.

---

## WebSocket

```
ws://localhost:8080/ws
```

Real-time event stream. Connect to receive events as they happen.

**Authentication:** Pass API key as `?token=YOUR_API_KEY`

**Message format:**
```json
{
  "type": "new_event",
  "data": {...},
  "timestamp": "2024-01-30T..."
}
```
