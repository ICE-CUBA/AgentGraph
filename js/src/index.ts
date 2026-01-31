/**
 * AgentGraph TypeScript/JavaScript SDK
 * 
 * The Memory Layer for AI Agents - Track, visualize, and share context between AI agents.
 * 
 * @example
 * ```typescript
 * import { AgentGraphClient } from 'agentgraph';
 * 
 * const client = new AgentGraphClient({ apiKey: 'your-api-key' });
 * 
 * // Log events
 * await client.log('tool.call', 'search', { query: 'AI news' });
 * 
 * // Query activities
 * const result = await client.query('what happened today?');
 * 
 * // Create entities and relationships
 * const userId = await client.createEntity('user', 'Alice');
 * const taskId = await client.createEntity('task', 'Data Analysis');
 * await client.createRelationship(userId, taskId, 'owns');
 * ```
 */

// ==================== Types ====================

export interface AgentGraphConfig {
  /** API key for authentication */
  apiKey?: string;
  /** AgentGraph server URL (default: http://localhost:8080) */
  baseUrl?: string;
  /** Auto-create a session on init (default: true) */
  autoSession?: boolean;
  /** Session name for auto-created session */
  sessionName?: string;
  /** Request timeout in ms (default: 30000) */
  timeout?: number;
}

export interface Event {
  id: string;
  agent_id: string;
  session_id?: string;
  type: string;
  action: string;
  description?: string;
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  tags: string[];
  metadata: Record<string, unknown>;
  status: 'success' | 'error' | 'pending';
  error_message?: string;
  duration_ms?: number;
  parent_event_id?: string;
  timestamp: string;
}

export interface Entity {
  id: string;
  type: string;
  name: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Relationship {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  type: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Session {
  id: string;
  agent_id: string;
  name?: string;
  user_id?: string;
  metadata: Record<string, unknown>;
  started_at: string;
  ended_at?: string;
}

export interface Agent {
  id: string;
  name: string;
  platform: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface QueryResult {
  answer?: string;
  events: Event[];
  entities: Entity[];
  summary?: string;
}

export interface GraphData {
  nodes: Array<{
    id: string;
    type: string;
    name: string;
    metadata: Record<string, unknown>;
  }>;
  links: Array<{
    source: string;
    target: string;
    type: string;
    metadata: Record<string, unknown>;
  }>;
}

export interface SemanticSearchResult {
  event: Event;
  similarity: number;
}

export interface LogOptions {
  description?: string;
  inputData?: Record<string, unknown>;
  outputData?: Record<string, unknown>;
  tags?: string[];
  metadata?: Record<string, unknown>;
  status?: 'success' | 'error' | 'pending';
  errorMessage?: string;
  durationMs?: number;
  parentEventId?: string;
}

export interface ShareEvent {
  topic: string;
  action?: string;
  description?: string;
  entityId?: string;
  entityType?: string;
  targetAgentIds?: string[];
  data?: Record<string, unknown>;
  priority?: number;
}

// ==================== Client ====================

export class AgentGraphClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly timeout: number;
  private sessionId?: string;
  private parentEventId?: string;

  constructor(config: AgentGraphConfig = {}) {
    this.baseUrl = (config.baseUrl || 'http://localhost:8080').replace(/\/$/, '');
    this.apiKey = config.apiKey || process.env.AGENTGRAPH_API_KEY || '';
    this.timeout = config.timeout || 30000;

    if (config.autoSession !== false) {
      // Create session asynchronously
      this.createSession(config.sessionName || 'Auto Session').then(id => {
        this.sessionId = id;
      }).catch(() => {
        // Silently fail if server isn't available
      });
    }
  }

  private async request<T>(method: string, endpoint: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`AgentGraph API error: ${response.status} ${error}`);
      }

      return await response.json();
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ==================== Core Methods ====================

  /**
   * Log an event to AgentGraph.
   */
  async log(
    eventType: string,
    action: string,
    options: LogOptions = {}
  ): Promise<string> {
    const result = await this.request<{ id: string }>('POST', '/events', {
      type: eventType,
      session_id: this.sessionId,
      action,
      description: options.description || '',
      input_data: options.inputData || {},
      output_data: options.outputData || {},
      tags: options.tags || [],
      metadata: options.metadata || {},
      status: options.status || 'success',
      error_message: options.errorMessage,
      duration_ms: options.durationMs,
      parent_event_id: options.parentEventId || this.parentEventId,
    });
    return result.id;
  }

  /**
   * Log multiple events at once.
   */
  async logBatch(events: Array<{ type: string; action: string } & LogOptions>): Promise<string[]> {
    const payload = events.map(e => ({
      type: e.type,
      session_id: this.sessionId,
      action: e.action,
      description: e.description || '',
      input_data: e.inputData || {},
      output_data: e.outputData || {},
      tags: e.tags || [],
      metadata: e.metadata || {},
      status: e.status || 'success',
      error_message: e.errorMessage,
      duration_ms: e.durationMs,
      parent_event_id: e.parentEventId || this.parentEventId,
    }));

    const result = await this.request<{ event_ids: string[] }>('POST', '/events/batch', { events: payload });
    return result.event_ids;
  }

  /**
   * Create a new session.
   */
  async createSession(name?: string, userId?: string, metadata?: Record<string, unknown>): Promise<string> {
    const result = await this.request<{ id: string }>('POST', '/sessions', {
      name: name || '',
      user_id: userId,
      metadata: metadata || {},
    });
    return result.id;
  }

  /**
   * Set the current session ID.
   */
  setSession(sessionId: string): void {
    this.sessionId = sessionId;
  }

  // ==================== Entity & Relationship Methods ====================

  /**
   * Create an entity in the knowledge graph.
   */
  async createEntity(
    type: string,
    name: string,
    metadata?: Record<string, unknown>
  ): Promise<string> {
    const result = await this.request<{ id: string }>('POST', '/entities', {
      type,
      name,
      metadata: metadata || {},
    });
    return result.id;
  }

  /**
   * Get an entity by ID.
   */
  async getEntity(entityId: string): Promise<Entity> {
    return this.request<Entity>('GET', `/entities/${entityId}`);
  }

  /**
   * Create a relationship between entities.
   */
  async createRelationship(
    sourceId: string,
    targetId: string,
    type: string,
    metadata?: Record<string, unknown>
  ): Promise<string> {
    const result = await this.request<{ id: string }>('POST', '/relationships', {
      source_entity_id: sourceId,
      target_entity_id: targetId,
      type,
      metadata: metadata || {},
    });
    return result.id;
  }

  // ==================== Query Methods ====================

  /**
   * Ask a natural language question about agent activity.
   */
  async query(question: string, context?: Record<string, unknown>): Promise<QueryResult> {
    return this.request<QueryResult>('POST', '/query', {
      question,
      context: context || {},
    });
  }

  /**
   * Search events by keyword.
   */
  async searchEvents(query: string, limit = 50): Promise<Event[]> {
    const result = await this.request<{ events: Event[] }>('GET', `/search/events?q=${encodeURIComponent(query)}&limit=${limit}`);
    return result.events;
  }

  /**
   * Search entities by name or metadata.
   */
  async searchEntities(query: string, entityType?: string, limit = 50): Promise<Entity[]> {
    let url = `/search/entities?q=${encodeURIComponent(query)}&limit=${limit}`;
    if (entityType) {
      url += `&entity_type=${encodeURIComponent(entityType)}`;
    }
    const result = await this.request<{ entities: Entity[] }>('GET', url);
    return result.entities;
  }

  /**
   * Semantic search using embeddings.
   */
  async semanticSearch(query: string, limit = 10): Promise<SemanticSearchResult[]> {
    const result = await this.request<{ results: SemanticSearchResult[] }>(
      'GET',
      `/search/semantic?q=${encodeURIComponent(query)}&limit=${limit}`
    );
    return result.results;
  }

  /**
   * Get recent events.
   */
  async getEvents(limit = 50, eventType?: string): Promise<Event[]> {
    let url = `/events?limit=${limit}`;
    if (eventType) {
      url += `&type=${encodeURIComponent(eventType)}`;
    }
    const result = await this.request<{ events: Event[] }>('GET', url);
    return result.events;
  }

  /**
   * Get the knowledge graph.
   */
  async getGraph(): Promise<GraphData> {
    return this.request<GraphData>('GET', '/graph/data');
  }

  // ==================== Sharing Methods ====================

  /**
   * Connect to the sharing hub.
   */
  async shareConnect(): Promise<{ connected_agents: Agent[] }> {
    return this.request('POST', '/share/connect');
  }

  /**
   * Disconnect from the sharing hub.
   */
  async shareDisconnect(): Promise<void> {
    await this.request('POST', '/share/disconnect');
  }

  /**
   * Subscribe to events from other agents.
   */
  async shareSubscribe(options: {
    topics?: string[];
    entityIds?: string[];
    sourceAgentIds?: string[];
  } = {}): Promise<string> {
    const result = await this.request<{ subscription_id: string }>('POST', '/share/subscribe', {
      topics: options.topics || [],
      entity_ids: options.entityIds || [],
      source_agent_ids: options.sourceAgentIds || [],
    });
    return result.subscription_id;
  }

  /**
   * Publish a context event to other agents.
   */
  async sharePublish(event: ShareEvent): Promise<{ recipients: number }> {
    return this.request('POST', '/share/publish', {
      topic: event.topic,
      action: event.action || '',
      description: event.description || '',
      entity_id: event.entityId,
      entity_type: event.entityType,
      target_agent_ids: event.targetAgentIds || [],
      data: event.data || {},
      priority: event.priority || 0,
    });
  }

  /**
   * Get connected agents.
   */
  async shareGetAgents(): Promise<Agent[]> {
    const result = await this.request<{ connected_agents: Agent[] }>('GET', '/share/agents');
    return result.connected_agents;
  }

  /**
   * Claim exclusive work on an entity.
   */
  async shareClaim(entityId: string): Promise<boolean> {
    try {
      await this.request('POST', `/share/claim/${entityId}`);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Release a claim on an entity.
   */
  async shareRelease(entityId: string): Promise<boolean> {
    const result = await this.request<{ success: boolean }>('POST', `/share/release/${entityId}`);
    return result.success;
  }

  // ==================== Convenience Methods ====================

  /**
   * Log a tool call.
   */
  async logToolCall(
    toolName: string,
    input: Record<string, unknown>,
    output?: Record<string, unknown>,
    options: Omit<LogOptions, 'inputData' | 'outputData'> = {}
  ): Promise<string> {
    return this.log('tool.call', toolName, {
      ...options,
      inputData: input,
      outputData: output,
    });
  }

  /**
   * Log a decision.
   */
  async logDecision(
    decision: string,
    reasoning?: string,
    options?: { confidence?: number; alternatives?: string[] }
  ): Promise<string> {
    return this.log('decision', decision, {
      description: reasoning,
      metadata: {
        confidence: options?.confidence,
        alternatives: options?.alternatives,
      },
    });
  }

  /**
   * Log an error.
   */
  async logError(
    error: Error | string,
    action?: string,
    context?: Record<string, unknown>
  ): Promise<string> {
    const errorMessage = error instanceof Error ? error.message : error;
    const errorType = error instanceof Error ? error.constructor.name : 'Error';
    
    return this.log('action.error', action || 'error', {
      status: 'error',
      errorMessage,
      metadata: {
        error_type: errorType,
        context: context || {},
      },
    });
  }

  // ==================== Tracking Utilities ====================

  /**
   * Track a function call with automatic logging.
   */
  track<T extends (...args: unknown[]) => unknown>(
    fn: T,
    options: { eventType?: string; action?: string } = {}
  ): T {
    const client = this;
    const eventType = options.eventType || 'action.complete';
    const action = options.action || fn.name || 'anonymous';

    return (async function (...args: Parameters<T>): Promise<ReturnType<T>> {
      const startTime = Date.now();
      
      try {
        const result = await fn(...args);
        const durationMs = Date.now() - startTime;

        await client.log(eventType, action, {
          inputData: { args: args.map(a => String(a).slice(0, 100)) },
          outputData: result !== undefined ? { result: String(result).slice(0, 500) } : undefined,
          durationMs,
          status: 'success',
        });

        return result as ReturnType<T>;
      } catch (error) {
        const durationMs = Date.now() - startTime;
        
        await client.log('action.error', action, {
          inputData: { args: args.map(a => String(a).slice(0, 100)) },
          durationMs,
          status: 'error',
          errorMessage: error instanceof Error ? error.message : String(error),
        });

        throw error;
      }
    }) as T;
  }

  /**
   * Create a child context for grouping events.
   */
  async withContext<T>(
    action: string,
    fn: () => Promise<T>,
    options: { eventType?: string; metadata?: Record<string, unknown> } = {}
  ): Promise<T> {
    const startTime = Date.now();
    const startEventId = await this.log('action.start', action, {
      metadata: options.metadata,
    });

    const oldParent = this.parentEventId;
    this.parentEventId = startEventId;

    try {
      const result = await fn();
      const durationMs = Date.now() - startTime;

      await this.log(options.eventType || 'action.complete', action, {
        durationMs,
        status: 'success',
        parentEventId: startEventId,
        metadata: options.metadata,
      });

      return result;
    } catch (error) {
      const durationMs = Date.now() - startTime;

      await this.log('action.error', action, {
        durationMs,
        status: 'error',
        errorMessage: error instanceof Error ? error.message : String(error),
        parentEventId: startEventId,
        metadata: options.metadata,
      });

      throw error;
    } finally {
      this.parentEventId = oldParent;
    }
  }

  // ==================== Health Check ====================

  /**
   * Check if the AgentGraph server is healthy.
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.request('GET', '/health');
      return true;
    } catch {
      return false;
    }
  }
}

// Default export
export default AgentGraphClient;
