# 🕸️ AgentGraph

**Infrastructure for Multi-Agent AI Systems**

The coordination layer that lets AI agents discover, communicate, and collaborate. Build systems where agents work together — not just alone.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/ICE-CUBA/AgentGraph/actions/workflows/ci.yml/badge.svg)](https://github.com/ICE-CUBA/AgentGraph/actions)

## 🌌 The Vision

Today's AI agents are isolated. Each one starts from scratch, knows nothing about others, and loses everything between sessions.

But the future isn't single agents — it's **agent networks**:
- Teams of specialized agents collaborating on complex problems
- Agents that learn from each other's experiences  
- Swarms that coordinate without central control
- Agent marketplaces, reputation systems, collective intelligence

**AgentGraph is the infrastructure that makes this possible.**

## 🎯 Why AgentGraph?

| Single-Agent Tools | AgentGraph |
|-------------------|------------|
| Memory for one agent | Shared knowledge across agents |
| Trace one agent's actions | Coordinate multiple agents' activities |
| Debug after the fact | Prevent conflicts in real-time |
| Isolated context | Connected intelligence |

### Core Capabilities

🔗 **Knowledge Graph** — Not flat memories, but entities and relationships that agents can query and extend

📡 **Real-Time Coordination** — Pub/sub events, WebSocket streaming, instant updates across all connected agents

🤝 **Collaboration Protocol** — Agents claim resources, share context, resolve conflicts automatically

🔍 **Semantic Search** — Find relevant knowledge using natural language, powered by embeddings

🛠️ **Framework Agnostic** — Works with LangChain, OpenAI Assistants, CrewAI, AutoGen, or your own agents

## 📦 Installation

```bash
# Python
pip install agentgraph-ai

# With all integrations
pip install agentgraph-ai[all]

# JavaScript/TypeScript  
npm install agentgraph-ai
```

## 🚀 Quick Start

### 1. Start the Server

```bash
pip install agentgraph-ai[server]
python -m agentgraph.api.server
# Server running at http://localhost:8080
```

### 2. Connect Your First Agent

```python
from agentgraph import AgentGraphClient

client = AgentGraphClient(api_key="your-key")

# Log what the agent does
client.log("tool.call", "web_search", {
    "inputData": {"query": "latest AI research"},
    "outputData": {"results": 10}
})

# Build knowledge
doc_id = client.create_entity("document", "Research Report")
client.create_relationship(agent_id, doc_id, "created")
```

### 3. Connect Multiple Agents

```python
# Agent 1: Research Agent
research_client = AgentGraphClient(api_key="research-agent-key")
research_client.share_connect()
research_client.share_subscribe(topics=["task.assigned"])

# Agent 2: Writer Agent  
writer_client = AgentGraphClient(api_key="writer-agent-key")
writer_client.share_connect()

# Writer requests help from Research Agent
writer_client.share_publish({
    "topic": "task.assigned",
    "action": "research_request",
    "description": "Find statistics on AI adoption",
    "data": {"deadline": "1 hour", "priority": "high"}
})

# Research Agent receives it instantly via WebSocket
# Agents are now collaborating!
```

### 4. Prevent Conflicts

```python
# Agent 1 claims exclusive work on a customer
customer_id = "customer-42"
if client.share_claim(customer_id):
    # Safe to work — no other agent will touch this
    process_customer(customer_id)
    client.share_release(customer_id)
else:
    # Another agent is handling it
    wait_or_do_something_else()
```

## 🤖 MCP Integration (Claude, Cursor, Cline)

AgentGraph works with any MCP-compatible AI coding tool:

```bash
# Add to Claude Code
claude mcp add agentgraph -- python -m agentgraph.mcp

# Or run as HTTP server
python -m agentgraph.mcp --transport http --port 8081
```

Available tools: `query_agentgraph`, `log_event`, `search_events`, `semantic_search`, `create_entity`, `create_relationship`, `get_graph_data`, and more.

## 💻 CLI

```bash
# Natural language queries
agentgraph query "what did my agents work on today?"

# List recent activity
agentgraph events --limit 50

# View knowledge graph
agentgraph graph

# Search semantically
agentgraph search "customer onboarding" --semantic
```

## 🔌 Integrations

### LangChain
```python
from agentgraph import AgentGraphClient, LangChainCallback

client = AgentGraphClient(api_key="...")
callback = LangChainCallback(client)
llm = ChatOpenAI(callbacks=[callback])
# All LLM calls automatically tracked
```

### OpenAI Assistants
```python
from agentgraph import OpenAIAssistantsTracker

tracker = OpenAIAssistantsTracker(agentgraph_api_key="...")
client = tracker.wrap(OpenAI())
# All assistant runs automatically tracked
```

### CrewAI
```python
from agentgraph import CrewAITracker

tracker = CrewAITracker(agentgraph_api_key="...")
crew = tracker.wrap(my_crew)
# All crew activities tracked, including delegation
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AgentGraph                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Agent A   │  │   Agent B   │  │   Agent C   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│                   ┌──────▼──────┐                           │
│                   │  Sharing    │  ← Real-time pub/sub      │
│                   │    Hub      │                           │
│                   └──────┬──────┘                           │
│                          │                                  │
│         ┌────────────────┼────────────────┐                 │
│         │                │                │                 │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐        │
│  │   Events    │  │  Entities   │  │   Search    │        │
│  │   Store     │  │   Graph     │  │   Index     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🗺️ Roadmap

### ✅ Shipped
- [x] Event logging and querying
- [x] Entity/relationship knowledge graph
- [x] Real-time WebSocket streaming
- [x] Cross-agent sharing protocol
- [x] Semantic search with embeddings
- [x] LangChain, OpenAI, CrewAI integrations
- [x] MCP server for AI coding tools
- [x] CLI interface
- [x] Python + TypeScript SDKs

### 🔜 Coming Soon
- [ ] Agent Registry — discovery and capability advertising
- [ ] Trust & Reputation — track agent reliability over time
- [ ] Federated Mode — connect multiple AgentGraph instances
- [ ] Evaluation Suite — benchmark agent collaboration
- [ ] Cloud Platform — managed hosting

### 🌌 Future Vision
- [ ] Agent-to-agent protocols (standardized communication)
- [ ] Collective learning (agents improve from shared experiences)
- [ ] Economic primitives (value exchange between agents)
- [ ] Decentralized agent networks

## 🆚 How We're Different

| Feature | AgentGraph | Mem0 | Langfuse | LangSmith |
|---------|------------|------|----------|-----------|
| **Multi-agent coordination** | ✅ Native | ❌ | ❌ | ❌ |
| **Real-time sharing** | ✅ WebSocket | ❌ | ❌ | ❌ |
| **Knowledge graph** | ✅ Entities + relationships | Flat memories | Traces only | Traces only |
| **Conflict prevention** | ✅ Claims system | ❌ | ❌ | ❌ |
| **Observability** | ✅ | ❌ | ✅ | ✅ |
| **Semantic search** | ✅ | ✅ | ❌ | ✅ |
| **Self-hostable** | ✅ | ✅ | ✅ | Enterprise |

**We're not building memory for single agents. We're building infrastructure for agent networks.**

## 📖 Documentation

- [API Reference](./docs/api.md)
- [SDK Guide](./docs/sdk.md)
- [Multi-Agent Tutorial](./examples/multi_agent_demo.py)
- [MCP Integration](./docs/mcp.md)

## 🤝 Contributing

We're building the future of multi-agent AI. Contributions welcome!

```bash
git clone https://github.com/ICE-CUBA/AgentGraph.git
cd AgentGraph
pip install -e ".[all]"
pytest tests/
```

## 📄 License

MIT — build whatever you want.

---

<p align="center">
  <b>The future is multi-agent. Start building it today.</b>
  <br><br>
  <a href="https://github.com/ICE-CUBA/AgentGraph">GitHub</a> ·
  <a href="https://github.com/ICE-CUBA/AgentGraph/issues">Issues</a> ·
  <a href="https://github.com/ICE-CUBA/AgentGraph/discussions">Discussions</a>
</p>
