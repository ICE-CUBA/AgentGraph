"""
AgentGraph Storage Layer

SQLite-based storage for MVP. Can be upgraded to PostgreSQL/Neo4j later.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.schema import Agent, Entity, Event, Relationship, Session


class Database:
    """SQLite database for AgentGraph."""
    
    def __init__(self, db_path: str = "agentgraph.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Agents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    platform TEXT,
                    owner_id TEXT,
                    api_key TEXT UNIQUE,
                    config TEXT DEFAULT '{}',
                    capabilities TEXT DEFAULT '[]',
                    is_active INTEGER DEFAULT 1,
                    last_seen TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    user_id TEXT,
                    name TEXT,
                    metadata TEXT DEFAULT '{}',
                    is_active INTEGER DEFAULT 1,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    FOREIGN KEY (agent_id) REFERENCES agents(id)
                )
            """)
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    action TEXT,
                    description TEXT,
                    input_data TEXT,
                    output_data TEXT,
                    parent_event_id TEXT,
                    related_entity_ids TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'success',
                    error_message TEXT,
                    timestamp TEXT NOT NULL,
                    duration_ms INTEGER,
                    FOREIGN KEY (agent_id) REFERENCES agents(id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            # Entities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            
            # Relationships table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    created_by_event_id TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    valid_until TEXT,
                    FOREIGN KEY (source_entity_id) REFERENCES entities(id),
                    FOREIGN KEY (target_entity_id) REFERENCES entities(id),
                    FOREIGN KEY (created_by_event_id) REFERENCES events(id)
                )
            """)
            
            # Indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_entity_id)")
    
    # ==================== Agents ====================
    
    def create_agent(self, agent: Agent) -> Agent:
        """Create a new agent."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agents (id, name, platform, owner_id, api_key, config, capabilities, is_active, last_seen, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent.id, agent.name, agent.platform, agent.owner_id, agent.api_key,
                json.dumps(agent.config), json.dumps(agent.capabilities),
                1 if agent.is_active else 0,
                agent.last_seen.isoformat() if agent.last_seen else None,
                agent.created_at.isoformat()
            ))
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_agent(row)
        return None
    
    def get_agent_by_api_key(self, api_key: str) -> Optional[Agent]:
        """Get agent by API key."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agents WHERE api_key = ?", (api_key,))
            row = cursor.fetchone()
            if row:
                return self._row_to_agent(row)
        return None
    
    def list_agents(self, owner_id: Optional[str] = None) -> List[Agent]:
        """List all agents."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if owner_id:
                cursor.execute("SELECT * FROM agents WHERE owner_id = ?", (owner_id,))
            else:
                cursor.execute("SELECT * FROM agents")
            return [self._row_to_agent(row) for row in cursor.fetchall()]
    
    def update_agent_last_seen(self, agent_id: str):
        """Update agent's last seen timestamp."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agents SET last_seen = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), agent_id)
            )
    
    def _row_to_agent(self, row) -> Agent:
        return Agent(
            id=row["id"],
            name=row["name"],
            platform=row["platform"] or "",
            owner_id=row["owner_id"],
            api_key=row["api_key"],
            config=json.loads(row["config"]) if row["config"] else {},
            capabilities=json.loads(row["capabilities"]) if row["capabilities"] else [],
            is_active=bool(row["is_active"]),
            last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    # ==================== Events ====================
    
    def create_event(self, event: Event) -> Event:
        """Create a new event."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (id, type, agent_id, user_id, session_id, action, description,
                    input_data, output_data, parent_event_id, related_entity_ids, tags, metadata,
                    status, error_message, timestamp, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id, event.type.value, event.agent_id, event.user_id, event.session_id,
                event.action, event.description,
                json.dumps(event.input_data) if event.input_data else None,
                json.dumps(event.output_data) if event.output_data else None,
                event.parent_event_id,
                json.dumps(event.related_entity_ids),
                json.dumps(event.tags),
                json.dumps(event.metadata),
                event.status, event.error_message,
                event.timestamp.isoformat(), event.duration_ms
            ))
        return event
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_event(row)
        return None
    
    def list_events(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Event]:
        """List events with filters."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM events WHERE 1=1"
            params = []
            
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            if event_type:
                query += " AND type = ?"
                params.append(event_type)
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def _row_to_event(self, row) -> Event:
        from ..core.schema import EventType
        return Event(
            id=row["id"],
            type=EventType(row["type"]),
            agent_id=row["agent_id"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            action=row["action"] or "",
            description=row["description"] or "",
            input_data=json.loads(row["input_data"]) if row["input_data"] else None,
            output_data=json.loads(row["output_data"]) if row["output_data"] else None,
            parent_event_id=row["parent_event_id"],
            related_entity_ids=json.loads(row["related_entity_ids"]) if row["related_entity_ids"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            status=row["status"],
            error_message=row["error_message"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            duration_ms=row["duration_ms"]
        )
    
    # ==================== Entities ====================
    
    def create_entity(self, entity: Entity) -> Entity:
        """Create a new entity."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entities (id, type, name, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                entity.id, entity.type.value, entity.name,
                json.dumps(entity.metadata), entity.created_at.isoformat()
            ))
        return entity
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_entity(row)
        return None
    
    def _row_to_entity(self, row) -> Entity:
        from ..core.schema import EntityType
        return Entity(
            id=row["id"],
            type=EntityType(row["type"]),
            name=row["name"] or "",
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    # ==================== Relationships ====================
    
    def create_relationship(self, rel: Relationship) -> Relationship:
        """Create a new relationship."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO relationships (id, type, source_entity_id, target_entity_id,
                    created_by_event_id, metadata, created_at, valid_until)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rel.id, rel.type.value, rel.source_entity_id, rel.target_entity_id,
                rel.created_by_event_id, json.dumps(rel.metadata),
                rel.created_at.isoformat(),
                rel.valid_until.isoformat() if rel.valid_until else None
            ))
        return rel
    
    def get_relationships(
        self,
        entity_id: str,
        direction: str = "both"  # "outgoing", "incoming", "both"
    ) -> List[Relationship]:
        """Get relationships for an entity."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            if direction == "outgoing":
                cursor.execute("SELECT * FROM relationships WHERE source_entity_id = ?", (entity_id,))
            elif direction == "incoming":
                cursor.execute("SELECT * FROM relationships WHERE target_entity_id = ?", (entity_id,))
            else:
                cursor.execute(
                    "SELECT * FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?",
                    (entity_id, entity_id)
                )
            
            return [self._row_to_relationship(row) for row in cursor.fetchall()]
    
    def _row_to_relationship(self, row) -> Relationship:
        from ..core.schema import RelationType
        return Relationship(
            id=row["id"],
            type=RelationType(row["type"]),
            source_entity_id=row["source_entity_id"],
            target_entity_id=row["target_entity_id"],
            created_by_event_id=row["created_by_event_id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            valid_until=datetime.fromisoformat(row["valid_until"]) if row["valid_until"] else None
        )
    
    # ==================== Sessions ====================
    
    def create_session(self, session: Session) -> Session:
        """Create a new session."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (id, agent_id, user_id, name, metadata, is_active, started_at, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.id, session.agent_id, session.user_id, session.name,
                json.dumps(session.metadata), 1 if session.is_active else 0,
                session.started_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else None
            ))
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_session(row)
        return None
    
    def _row_to_session(self, row) -> Session:
        return Session(
            id=row["id"],
            agent_id=row["agent_id"],
            user_id=row["user_id"],
            name=row["name"] or "",
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            is_active=bool(row["is_active"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None
        )
    
    # ==================== Analytics ====================
    
    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for an agent."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Total events
            cursor.execute("SELECT COUNT(*) FROM events WHERE agent_id = ?", (agent_id,))
            total_events = cursor.fetchone()[0]
            
            # Events by type
            cursor.execute("""
                SELECT type, COUNT(*) as count FROM events 
                WHERE agent_id = ? GROUP BY type
            """, (agent_id,))
            events_by_type = {row["type"]: row["count"] for row in cursor.fetchall()}
            
            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE agent_id = ?", (agent_id,))
            total_sessions = cursor.fetchone()[0]
            
            # Error rate
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'error' THEN 1 END) as errors,
                    COUNT(*) as total
                FROM events WHERE agent_id = ?
            """, (agent_id,))
            row = cursor.fetchone()
            error_rate = row["errors"] / row["total"] if row["total"] > 0 else 0
            
            return {
                "agent_id": agent_id,
                "total_events": total_events,
                "events_by_type": events_by_type,
                "total_sessions": total_sessions,
                "error_rate": round(error_rate, 4)
            }
