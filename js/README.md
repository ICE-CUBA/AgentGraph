# AgentGraph JavaScript/TypeScript SDK

The Memory Layer for AI Agents - Track, visualize, and share context between AI agents.

## Installation

```bash
npm install agentgraph-ai
# or
yarn add agentgraph-ai
# or
pnpm add agentgraph-ai
```

## Quick Start

```typescript
import { AgentGraphClient } from 'agentgraph-ai';

// Initialize client
const client = new AgentGraphClient({
  apiKey: 'your-api-key',  // or set AGENTGRAPH_API_KEY env var
  baseUrl: 'http://localhost:8080',  // optional, this is the default
});

// Log events
await client.log('tool.call', 'search', {
  inputData: { query: 'AI news' },
  outputData: { results: 10 },
});

// Query activities
const result = await client.query('what happened today?');
console.log(result.answer);
console.log(result.events);

// Create entities and relationships
const userId = await client.createEntity('user', 'Alice', { role: 'admin' });
const taskId = await client.createEntity('task', 'Data Analysis', { priority: 'high' });
await client.createRelationship(userId, taskId, 'owns');

// Get the knowledge graph
const graph = await client.getGraph();
console.log(`${graph.nodes.length} nodes, ${graph.links.length} relationships`);
```

## Features

### Event Logging

```typescript
// Simple event
await client.log('action.complete', 'process_data');

// With full options
await client.log('tool.call', 'api_request', {
  description: 'Fetched user data',
  inputData: { userId: '123' },
  outputData: { name: 'Alice' },
  tags: ['api', 'user'],
  metadata: { endpoint: '/users/123' },
  durationMs: 150,
});

// Convenience methods
await client.logToolCall('search', { query: 'test' }, { results: [] });
await client.logDecision('use_cache', 'Data is fresh', { confidence: 0.95 });
await client.logError(new Error('Connection failed'), 'db_connect');

// Batch logging
await client.logBatch([
  { type: 'action.start', action: 'pipeline' },
  { type: 'tool.call', action: 'step1' },
  { type: 'tool.call', action: 'step2' },
  { type: 'action.complete', action: 'pipeline' },
]);
```

### Querying

```typescript
// Natural language query
const result = await client.query('what tools were used today?');

// Keyword search
const events = await client.searchEvents('error', 50);

// Semantic search (requires embeddings)
const similar = await client.semanticSearch('database operations');

// Get recent events
const recent = await client.getEvents(20, 'tool.call');
```

### Knowledge Graph

```typescript
// Create entities
const userId = await client.createEntity('user', 'Alice');
const docId = await client.createEntity('document', 'Report.pdf');

// Create relationships
await client.createRelationship(userId, docId, 'created');
await client.createRelationship(userId, docId, 'modified');

// Get graph data
const graph = await client.getGraph();
// Returns { nodes: [...], links: [...] } for D3.js visualization
```

### Cross-Agent Sharing

```typescript
// Connect to sharing hub
await client.shareConnect();

// Subscribe to events
await client.shareSubscribe({
  topics: ['decision.made', 'action.completed'],
  entityIds: ['customer-123'],
});

// Publish events to other agents
await client.sharePublish({
  topic: 'action.completed',
  action: 'data_processed',
  description: 'Processed customer data',
  entityId: 'customer-123',
  data: { records: 1000 },
});

// Claim exclusive work on an entity
const claimed = await client.shareClaim('customer-123');
if (claimed) {
  // Do work...
  await client.shareRelease('customer-123');
}
```

### Automatic Tracking

```typescript
// Track function calls
const trackedFn = client.track(async (x: number) => x * 2);
await trackedFn(5);  // Logs action.complete with input/output

// Context for grouping events
await client.withContext('complex_operation', async () => {
  await client.log('tool.call', 'step1');
  await client.log('tool.call', 'step2');
  await client.log('tool.call', 'step3');
});
// All nested logs are grouped under the parent context
```

## Environment Variables

- `AGENTGRAPH_API_KEY` - API key for authentication
- `AGENTGRAPH_URL` - Server URL (default: http://localhost:8080)

## Types

Full TypeScript types are included:

```typescript
import type {
  Event,
  Entity,
  Relationship,
  Session,
  Agent,
  QueryResult,
  GraphData,
  LogOptions,
  ShareEvent,
} from 'agentgraph-ai';
```

## License

MIT
