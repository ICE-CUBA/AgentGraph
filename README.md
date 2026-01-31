# 🧠 AgentGraph

**The Memory Layer for AI Agents**

Track, visualize, and share context between AI agents. Know what your agents are doing and help them collaborate.

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
- **Owner Dashboard** — See what's happening
- **Agent Queries** — Agents can ask "what happened?"
- **Cross-Agent Context** — Share knowledge between agents

## 🚀 Quick Start

### 1. Start the Server

```bash
pip install -r requirements.txt
python -m agentgraph.api.server
```

Server runs at `http://localhost:8080`

### 2. Register an Agent

```bash
curl -X POST http://localhost:8080/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "MyAgent", "platform": "custom"}'
```

Save the `api_key` from the response.

### 3. Use the SDK

```python
from agentgraph import AgentGraphClient

# Initialize client
client = AgentGraphClient(api_key="your-api-key")

# Log events
client.log("tool.call", action="search", input_data={"query": "AI news"})
client.log("decision", action="summarize", description="User wants a summary")

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
# Coming soon
```

### CrewAI

```python
# Coming soon
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

### Graph
- `GET /graph/timeline` — Get activity timeline

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

- [x] Core schema & storage
- [x] REST API
- [x] Python SDK
- [x] LangChain integration
- [ ] Dashboard UI
- [ ] Real-time WebSocket updates
- [ ] Agent-to-agent queries
- [ ] OpenAI Assistants integration
- [ ] CrewAI integration
- [ ] Graph visualization
- [ ] Hosted cloud version

## 📄 License

MIT

---

Built for the future of multi-agent AI systems. 🤖🤝🤖
