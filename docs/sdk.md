# AgentGraph SDK Guide

## Installation

```bash
pip install agentgraph-ai
```

## Quick Start (Zero Config)

The simplest way to use AgentGraph:

```python
from agentgraph import log, query

# Log events
log("searched for papers")
log("made a decision", type="decision")

# Query
result = query("what did I do?")
print(result["answer"])
```

No server setup needed — it starts automatically.

---

## Full SDK

For production use with custom configuration:

```python
from agentgraph import AgentGraphClient

client = AgentGraphClient(
    api_key="your-key",
    base_url="http://localhost:8080"
)
```

### Logging Events

```python
client.log(
    event_type="tool.call",
    action="web_search",
    input_data={"query": "AI research"},
    output_data={"results": 10},
    tags=["research"]
)
```

### Querying

```python
result = client.query("what did my agent work on?")
print(result["answer"])
```

### Creating Entities

```python
entity_id = client.create_entity(
    entity_type="user",
    name="Acme Corp",
    metadata={"industry": "tech"}
)
```

### Creating Relationships

```python
client.create_relationship(
    source_id=customer_id,
    target_id=project_id,
    relationship_type="owns"
)
```

---

## Agent Registry

### Registering

```python
from agentgraph import register_agent

agent = register_agent(
    name="MyBot",
    capabilities=["search", "summarize"],
    description="A helpful bot"
)

print(f"Registered: {agent.id}")
```

### Discovery

```python
from agentgraph import discover_agents

# Find all translators
translators = discover_agents("translate")

# Find with specific metadata
python_reviewers = discover_agents("code_review", languages="python")
```

### Heartbeat

```python
from agentgraph import heartbeat

# Call periodically to stay online
heartbeat(agent.id)
```

---

## Trust & Reputation

### Recording Work

```python
from agentgraph import record_task, complete_task

# Start a task
task_id = record_task(agent.id, "translate")

# Do the work...

# Mark complete
complete_task(task_id, "success")  # or "failure", "timeout"
```

### Rating

```python
from agentgraph import rate_agent

# Rate another agent's work
rate_agent(task_id, rating=0.9)  # 0.0 to 1.0
```

### Checking Trust

```python
from agentgraph import get_trust

score = get_trust(agent.id)  # 0.0 to 1.0
print(f"Trust: {score}")
```

---

## Multi-Agent Sharing

### Connecting

```python
from agentgraph import connect

connect("MyAgent")
```

### Sharing Context

```python
from agentgraph import share

share(
    "Found important insight",
    topic="research",
    data={"insight": "..."}
)
```

### Subscribing

```python
client.share_subscribe(topics=["task.assigned"])
```

### Claiming Resources

```python
if client.share_claim("customer-42"):
    # Safe to work
    process_customer("customer-42")
    client.share_release("customer-42")
```

---

## Decorators

### @track

Automatically track function calls:

```python
from agentgraph import track

@track
def my_agent_function(query):
    # Your logic
    return result

my_agent_function("test")
# Automatically logged with timing
```

---

## Integrations

### LangChain

```python
from agentgraph import AgentGraphClient, LangChainCallback

client = AgentGraphClient(api_key="...")
callback = LangChainCallback(client)

llm = ChatOpenAI(callbacks=[callback])
# All LLM calls tracked
```

### OpenAI Assistants

```python
from agentgraph import OpenAIAssistantsTracker

tracker = OpenAIAssistantsTracker(agentgraph_api_key="...")
client = tracker.wrap(OpenAI())
# Assistant runs tracked
```

### CrewAI

```python
from agentgraph import CrewAITracker

tracker = CrewAITracker(agentgraph_api_key="...")
crew = tracker.wrap(my_crew)
# Crew activities tracked
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENTGRAPH_URL` | Server URL | `http://localhost:8080` |
| `AGENTGRAPH_API_KEY` | API key | None |
