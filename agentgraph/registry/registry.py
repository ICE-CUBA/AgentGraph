"""
AgentRegistry - Core registry implementation with SQLite persistence.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .models import Agent, AgentStatus, Capability


class AgentRegistry:
    """
    Central registry for agent discovery and coordination.
    
    Features:
    - Register/unregister agents
    - Discover agents by capability
    - Track online/offline status with heartbeats
    - Persist to SQLite
    """
    
    # How long before an agent is considered offline (no heartbeat)
    HEARTBEAT_TIMEOUT = timedelta(minutes=5)
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the registry.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.agentgraph/registry.db
        """
        if db_path is None:
            db_dir = Path.home() / ".agentgraph"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "registry.db")
        
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    @property
    def _conn(self) -> sqlite3.Connection:
        """Thread-local database connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self):
        """Initialize database schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                capabilities TEXT DEFAULT '[]',
                status TEXT DEFAULT 'unknown',
                endpoint TEXT,
                metadata TEXT DEFAULT '{}',
                registered_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                trust_score REAL DEFAULT 0.5
            );
            
            CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
            CREATE INDEX IF NOT EXISTS idx_agents_last_seen ON agents(last_seen);
        """)
        self._conn.commit()
    
    def register(self, agent: Agent) -> Agent:
        """
        Register a new agent or update existing.
        
        Args:
            agent: Agent to register
            
        Returns:
            The registered agent
        """
        now = datetime.utcnow()
        agent.registered_at = now
        agent.last_seen = now
        agent.status = AgentStatus.ONLINE
        
        self._conn.execute("""
            INSERT OR REPLACE INTO agents 
            (id, name, description, capabilities, status, endpoint, metadata, registered_at, last_seen, trust_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent.id,
            agent.name,
            agent.description,
            json.dumps([c.to_dict() for c in agent.capabilities]),
            agent.status.value,
            agent.endpoint,
            json.dumps(agent.metadata),
            agent.registered_at.isoformat(),
            agent.last_seen.isoformat(),
            agent.trust_score,
        ))
        self._conn.commit()
        
        return agent
    
    def unregister(self, agent_id: str) -> bool:
        """
        Remove an agent from the registry.
        
        Args:
            agent_id: ID of agent to remove
            
        Returns:
            True if agent was removed, False if not found
        """
        cursor = self._conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        self._conn.commit()
        return cursor.rowcount > 0
    
    def get(self, agent_id: str) -> Optional[Agent]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent if found, None otherwise
        """
        row = self._conn.execute(
            "SELECT * FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
        
        if row:
            return self._row_to_agent(row)
        return None
    
    def discover(
        self,
        capability: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        online_only: bool = False,
        **capability_filters
    ) -> list[Agent]:
        """
        Discover agents matching criteria.
        
        Args:
            capability: Required capability name
            status: Required status
            online_only: Only return online/busy agents
            **capability_filters: Additional capability metadata filters
            
        Returns:
            List of matching agents
        """
        query = "SELECT * FROM agents WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        elif online_only:
            query += " AND status IN ('online', 'busy')"
        
        rows = self._conn.execute(query, params).fetchall()
        agents = [self._row_to_agent(row) for row in rows]
        
        # Filter by capability
        if capability:
            agents = [a for a in agents if a.has_capability(capability, **capability_filters)]
        
        # Update status based on heartbeat timeout
        for agent in agents:
            if self._is_stale(agent):
                agent.status = AgentStatus.OFFLINE
        
        return agents
    
    def heartbeat(self, agent_id: str) -> bool:
        """
        Update agent's last_seen timestamp.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if agent exists and was updated
        """
        now = datetime.utcnow().isoformat()
        cursor = self._conn.execute(
            "UPDATE agents SET last_seen = ?, status = 'online' WHERE id = ?",
            (now, agent_id)
        )
        self._conn.commit()
        return cursor.rowcount > 0
    
    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        Update an agent's status.
        
        Args:
            agent_id: Agent ID
            status: New status
            
        Returns:
            True if agent exists and was updated
        """
        now = datetime.utcnow().isoformat()
        cursor = self._conn.execute(
            "UPDATE agents SET status = ?, last_seen = ? WHERE id = ?",
            (status.value, now, agent_id)
        )
        self._conn.commit()
        return cursor.rowcount > 0
    
    def list_all(self) -> list[Agent]:
        """List all registered agents."""
        rows = self._conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [self._row_to_agent(row) for row in rows]
    
    def count(self, online_only: bool = False) -> int:
        """Count registered agents."""
        if online_only:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM agents WHERE status IN ('online', 'busy')"
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) FROM agents").fetchone()
        return row[0]
    
    def cleanup_stale(self) -> int:
        """
        Mark stale agents as offline.
        
        Returns:
            Number of agents marked offline
        """
        cutoff = (datetime.utcnow() - self.HEARTBEAT_TIMEOUT).isoformat()
        cursor = self._conn.execute(
            "UPDATE agents SET status = 'offline' WHERE last_seen < ? AND status != 'offline'",
            (cutoff,)
        )
        self._conn.commit()
        return cursor.rowcount
    
    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        """Convert database row to Agent object."""
        return Agent(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            capabilities=[Capability.from_dict(c) for c in json.loads(row["capabilities"])],
            status=AgentStatus(row["status"]),
            endpoint=row["endpoint"],
            metadata=json.loads(row["metadata"]),
            registered_at=datetime.fromisoformat(row["registered_at"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
            trust_score=row["trust_score"],
        )
    
    def _is_stale(self, agent: Agent) -> bool:
        """Check if agent hasn't sent heartbeat recently."""
        if agent.status == AgentStatus.OFFLINE:
            return False
        return datetime.utcnow() - agent.last_seen > self.HEARTBEAT_TIMEOUT
