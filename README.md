# 🧠 AgentGraph

**The Memory Layer for AI Agents**

Track, visualize, and share context between AI agents. Know what your agents are doing and help them collaborate.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 The Problem

AI agents today are isolated. They work, but:
- No memory of what they did
- Can't collaborate with other agents
- Owners can't audit their actions
- Context is lost between sessions

## 💡 The Solution

AgentGraph provides:
- **Activity Tracking** — Log everything agents do
- **Memory Graph** — Entities, relationships, and events
- **Owner Dashboard** — See what's happening in real-time
- **Graph Visualization** — Interactive D3.js entity relationship graphs
- **Agent Queries** — Agents can ask "what happened?"
- **Cross-Agent Context** — Share knowledge between agents

## 🚀 Quick Start

### 1. Start the Server

```bash
pip install -r requirements.txt
python -m agentgraph.api.server
```

Server runs at `http://localhost:8080`

### 2. Open the Dashboard

Navigate to `http://localhost:8080` in your browser:
- **📊 Events Tab** — Real-time activity feed
- **🕸️ Graph Tab** — Interactive entity relationship visualization

### 3. Register an Agent

```bash
curl -X POST http://localhost:8080/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "MyAgent", "platform": "langchain"}'
```

Save the `api_key` from the response.

### 4. Use the SDK

```python
from agentgraph import AgentGraphClient

# Initialize client
client = AgentGraphClient(api_key="your-api-key")

# Log events
client.log("tool.call", action="search", input_data={"query": "AI news"})
client.log("decision", action="summarize", description="User wants a summary")

# Create entities and relationships
user_id = client.create_entity("user", "Alice", {"role": "admin"})
task_id = client.create_entity("task", "Data Analysis", {"priority": "high"})
client.create_relationship(user_id, task_id, "owns")

# Use decorator for automatic tracking
@client.track()
def process_data(data):
    return analyze(data)

# Use context manager for duration tracking
with client.track_context("complex_operation"):
    step1()
    step2()
    step3()
```

### 5. Run the Demo

```bash
python demo.py
```

Creates sample agents, entities, relationships, and events to explore.

## 📊 Event Types

| Type | Description |
|------|-------------|
| `action.start` | Action started |
| `action.complete` | Action completed |
| `action.error` | Action failed |
| `tool.call` | Tool/function called |
| `tool.result` | Tool returned result |
| `decision` | Agent made a decision |
| `reasoning` | Agent reasoning step |
| `message.sent` | Message sent |
| `message.received` | Message received |
| `memory.store` | Stored in memory |
| `memory.retrieve` | Retrieved from memory |
| `state.change` | State changed |

## 🔗 Entity & Relationship Types

### Entities
| Type | Description |
|------|-------------|
| `agent` | AI agent |
| `user` | Human user |
| `task` | Task or job |
| `tool` | Tool or function |
| `document` | Document or file |
| `resource` | External resource |
| `session` | Conversation session |
| `custom` | Custom entity type |

### Relationships
| Type | Description |
|------|-------------|
| `created` | A created B |
| `modified` | A modified B |
| `referenced` | A referenced B |
| `depends_on` | A depends on B |
| `caused` | A caused B |
| `responded_to` | A responded to B |
| `part_of` | A is part of B |
| `owns` | A owns B |
| `delegated_to` | A delegated to B |
| `collaborated_with` | A collaborated with B |

## 🔌 Integrations

### LangChain

```python
from agentgraph import AgentGraphClient, LangChainCallback
from langchain.chat_models import ChatOpenAI

client = AgentGraphClient(api_key="...")
callback = LangChainCallback(client)

llm = ChatOpenAI(callbacks=[callback])
# All LLM calls are now tracked!
```

### OpenAI Assistants

```python
# Coming soon - Run/Step API integration
```

### CrewAI

```python
# Coming soon - Event hooks integration
```

## 📈 API Endpoints

### Agents
- `POST /agents` — Register agent (returns API key)
- `GET /agents` — List agents
- `GET /agents/{id}` — Get agent details
- `GET /agents/{id}/stats` — Get agent statistics

### Events
- `POST /events` — Log event (requires API key)
- `POST /events/batch` — Log multiple events
- `GET /events` — List events (with filters)
- `GET /events/{id}` — Get event details

### Sessions
- `POST /sessions` — Create session
- `GET /sessions/{id}` — Get session
- `GET /sessions/{id}/events` — Get session events

### Entities
- `POST /entities` — Create entity
- `GET /entities/{id}` — Get entity details
- `GET /entities/{id}/relationships` — Get entity relationships

### Relationships
- `POST /relationships` — Create relationship

### Graph & Visualization
- `GET /graph/data` — Get nodes + links for D3.js visualization
- `GET /graph/timeline` — Get activity timeline

### Health
- `GET /health` — Health check

## 🗄️ Data Model

```
┌─────────┐     logs      ┌─────────┐
│  Agent  │──────────────►│  Event  │
└─────────┘               └─────────┘
     │                         │
     │ has                     │ references
     ▼                         ▼
┌─────────┐              ┌──────────┐
│ Session │              │  Entity  │
└─────────┘              └──────────┘
                              │
                              │ connects
                              ▼
                        ┌──────────────┐
                        │ Relationship │
                        └──────────────┘
```

## 🛣️ Roadmap

### Phase 1: Passive Logging (✅ Complete)
- [x] Core schema & storage (SQLite)
- [x] REST API with authentication
- [x] Python SDK with decorators
- [x] LangChain integration
- [x] Dashboard UI (Vue.js + Tailwind)
- [x] D3.js graph visualization
- [x] Entity & relationship CRUD

### Phase 2: Agent Queries (🚧 In Progress)
- [ ] Real-time WebSocket updates
- [ ] Agent query interface ("what happened to X?")
- [ ] Semantic search over events
- [ ] OpenAI Assistants integration
- [ ] CrewAI integration

### Phase 3: Active Sharing
- [ ] Cross-agent context protocol
- [ ] Bi-directional event streaming
- [ ] Conflict detection & alerts
- [ ] Multi-tenant support

### Phase 4: Cloud Platform
- [ ] Hosted cloud version
- [ ] User authentication
- [ ] Team workspaces
- [ ] Usage analytics

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AgentGraph                           │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   SDK       │  │   REST API  │  │  Dashboard  │     │
│  │  (Python)   │  │  (FastAPI)  │  │  (Vue.js)   │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │             │
│         └────────────────┼────────────────┘             │
│                          │                              │
│                   ┌──────▼──────┐                       │
│                   │   Storage   │                       │
│                   │  (SQLite)   │                       │
│                   └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

## 📄 License

MIT

---

Built for the future of multi-agent AI systems. 🤖🤝🤖
