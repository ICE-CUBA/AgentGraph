"""
Trust & Reputation System for Agent Registry.

Tracks agent reliability through:
- Task completion rates
- Response times
- Error rates
- Peer ratings

Agents with higher trust scores get prioritized in discovery.
"""

import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Union


class TaskOutcome(str, Enum):
    """Outcome of a task assigned to an agent."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    PARTIAL = "partial"


@dataclass
class TaskRecord:
    """Record of a task performed by an agent."""
    id: str
    agent_id: str
    task_type: str
    outcome: TaskOutcome
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    rated_by: Optional[str] = None  # Agent ID that rated this
    rating: Optional[float] = None  # 0.0 to 1.0
    metadata: dict = field(default_factory=dict)


class ReputationTracker:
    """
    Tracks and calculates agent reputation scores.
    
    Trust score (0.0 to 1.0) is computed from:
    - Success rate (40% weight)
    - Response time percentile (20% weight)
    - Peer ratings (30% weight)
    - Consistency (10% weight)
    
    Scores decay over time — recent performance matters more.
    """
    
    # Scoring weights
    WEIGHT_SUCCESS_RATE = 0.40
    WEIGHT_RESPONSE_TIME = 0.20
    WEIGHT_PEER_RATING = 0.30
    WEIGHT_CONSISTENCY = 0.10
    
    # Time decay: half-life of 7 days
    DECAY_HALF_LIFE_DAYS = 7
    
    # Minimum tasks before trust score is meaningful
    MIN_TASKS_FOR_SCORE = 5
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the reputation tracker.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.agentgraph/reputation.db
        """
        if db_path is None:
            db_dir = Path.home() / ".agentgraph"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "reputation.db")
        
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
            CREATE TABLE IF NOT EXISTS task_records (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                error_message TEXT,
                rated_by TEXT,
                rating REAL,
                metadata TEXT DEFAULT '{}'
            );
            
            CREATE INDEX IF NOT EXISTS idx_task_agent ON task_records(agent_id);
            CREATE INDEX IF NOT EXISTS idx_task_outcome ON task_records(outcome);
            CREATE INDEX IF NOT EXISTS idx_task_started ON task_records(started_at);
            
            -- Aggregate stats cache (updated periodically)
            CREATE TABLE IF NOT EXISTS agent_stats (
                agent_id TEXT PRIMARY KEY,
                total_tasks INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                avg_duration_ms REAL,
                avg_rating REAL,
                trust_score REAL DEFAULT 0.5,
                last_updated TEXT
            );
        """)
        self._conn.commit()
    
    def record_task_start(
        self,
        agent_id: str,
        task_type: str,
        task_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Record the start of a task.
        
        Args:
            agent_id: Agent performing the task
            task_type: Type of task (e.g., "translate", "search")
            task_id: Optional task ID (auto-generated if not provided)
            metadata: Additional task metadata
            
        Returns:
            Task ID
        """
        import uuid
        import json
        
        task_id = task_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        self._conn.execute("""
            INSERT INTO task_records (id, agent_id, task_type, outcome, started_at, metadata)
            VALUES (?, ?, ?, 'pending', ?, ?)
        """, (task_id, agent_id, task_type, now, json.dumps(metadata or {})))
        self._conn.commit()
        
        return task_id
    
    def record_task_complete(
        self,
        task_id: str,
        outcome: TaskOutcome,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Record task completion.
        
        Args:
            task_id: Task ID from record_task_start
            outcome: Task outcome
            error_message: Error message if failed
            
        Returns:
            True if task was found and updated
        """
        now = datetime.utcnow()
        
        # Get start time to calculate duration
        row = self._conn.execute(
            "SELECT started_at FROM task_records WHERE id = ?", (task_id,)
        ).fetchone()
        
        if not row:
            return False
        
        started = datetime.fromisoformat(row["started_at"])
        duration_ms = int((now - started).total_seconds() * 1000)
        
        self._conn.execute("""
            UPDATE task_records 
            SET outcome = ?, completed_at = ?, duration_ms = ?, error_message = ?
            WHERE id = ?
        """, (outcome.value, now.isoformat(), duration_ms, error_message, task_id))
        self._conn.commit()
        
        # Update agent stats
        agent_id = self._conn.execute(
            "SELECT agent_id FROM task_records WHERE id = ?", (task_id,)
        ).fetchone()["agent_id"]
        self._update_agent_stats(agent_id)
        
        return True
    
    def rate_task(
        self,
        task_id: str,
        rating: float,
        rated_by: Optional[str] = None
    ) -> bool:
        """
        Rate a completed task.
        
        Args:
            task_id: Task ID
            rating: Rating from 0.0 (terrible) to 1.0 (excellent)
            rated_by: Agent ID of the rater (optional)
            
        Returns:
            True if task was found and rated
        """
        rating = max(0.0, min(1.0, rating))  # Clamp to [0, 1]
        
        cursor = self._conn.execute("""
            UPDATE task_records SET rating = ?, rated_by = ? WHERE id = ?
        """, (rating, rated_by, task_id))
        self._conn.commit()
        
        if cursor.rowcount > 0:
            agent_id = self._conn.execute(
                "SELECT agent_id FROM task_records WHERE id = ?", (task_id,)
            ).fetchone()["agent_id"]
            self._update_agent_stats(agent_id)
            return True
        
        return False
    
    def get_trust_score(self, agent_id: str) -> float:
        """
        Get the current trust score for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Trust score from 0.0 to 1.0 (0.5 is default/neutral)
        """
        row = self._conn.execute(
            "SELECT trust_score FROM agent_stats WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        
        if row:
            return row["trust_score"]
        return 0.5  # Default neutral score
    
    def get_agent_stats(self, agent_id: str) -> dict:
        """
        Get detailed statistics for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dictionary with stats
        """
        row = self._conn.execute(
            "SELECT * FROM agent_stats WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        
        if not row:
            return {
                "agent_id": agent_id,
                "total_tasks": 0,
                "success_rate": 0.0,
                "avg_duration_ms": None,
                "avg_rating": None,
                "trust_score": 0.5,
            }
        
        total = row["total_tasks"] or 1
        success_rate = (row["success_count"] or 0) / total
        
        return {
            "agent_id": agent_id,
            "total_tasks": row["total_tasks"],
            "success_count": row["success_count"],
            "failure_count": row["failure_count"],
            "success_rate": round(success_rate, 3),
            "avg_duration_ms": row["avg_duration_ms"],
            "avg_rating": row["avg_rating"],
            "trust_score": row["trust_score"],
            "last_updated": row["last_updated"],
        }
    
    def _update_agent_stats(self, agent_id: str):
        """Recalculate and cache agent statistics."""
        # Get recent tasks (last 30 days for decay calculation)
        cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        rows = self._conn.execute("""
            SELECT outcome, duration_ms, rating, started_at
            FROM task_records
            WHERE agent_id = ? AND started_at > ? AND outcome != 'pending'
            ORDER BY started_at DESC
        """, (agent_id, cutoff)).fetchall()
        
        if not rows:
            return
        
        total = len(rows)
        success = sum(1 for r in rows if r["outcome"] == "success")
        failure = sum(1 for r in rows if r["outcome"] in ("failure", "timeout"))
        
        durations = [r["duration_ms"] for r in rows if r["duration_ms"]]
        avg_duration = sum(durations) / len(durations) if durations else None
        
        ratings = [r["rating"] for r in rows if r["rating"] is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Calculate trust score
        trust_score = self._calculate_trust_score(
            success_rate=success / total if total > 0 else 0,
            avg_duration=avg_duration,
            avg_rating=avg_rating,
            total_tasks=total
        )
        
        now = datetime.utcnow().isoformat()
        
        self._conn.execute("""
            INSERT OR REPLACE INTO agent_stats 
            (agent_id, total_tasks, success_count, failure_count, avg_duration_ms, avg_rating, trust_score, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (agent_id, total, success, failure, avg_duration, avg_rating, trust_score, now))
        self._conn.commit()
    
    def _calculate_trust_score(
        self,
        success_rate: float,
        avg_duration: Optional[float],
        avg_rating: Optional[float],
        total_tasks: int
    ) -> float:
        """
        Calculate weighted trust score.
        
        Components:
        - Success rate (40%)
        - Response time score (20%) - faster is better
        - Peer rating (30%)
        - Consistency bonus (10%) - more tasks = more reliable score
        """
        # Success rate component
        success_component = success_rate * self.WEIGHT_SUCCESS_RATE
        
        # Response time component (normalized to 0-1 scale)
        # Assume < 1s is excellent, > 30s is poor
        if avg_duration:
            duration_score = max(0, 1 - (avg_duration / 30000))  # 30s = 30000ms
        else:
            duration_score = 0.5  # Neutral if no data
        time_component = duration_score * self.WEIGHT_RESPONSE_TIME
        
        # Peer rating component
        if avg_rating is not None:
            rating_component = avg_rating * self.WEIGHT_PEER_RATING
        else:
            rating_component = 0.5 * self.WEIGHT_PEER_RATING  # Neutral
        
        # Consistency component (log scale, max at ~100 tasks)
        import math
        consistency = min(1.0, math.log10(total_tasks + 1) / 2)
        consistency_component = consistency * self.WEIGHT_CONSISTENCY
        
        total_score = success_component + time_component + rating_component + consistency_component
        
        # Clamp to [0, 1]
        return round(max(0.0, min(1.0, total_score)), 3)
    
    def get_leaderboard(self, limit: int = 10) -> List[dict]:
        """
        Get top agents by trust score.
        
        Args:
            limit: Maximum number of agents to return
            
        Returns:
            List of agent stats, sorted by trust score
        """
        rows = self._conn.execute("""
            SELECT * FROM agent_stats 
            WHERE total_tasks >= ?
            ORDER BY trust_score DESC
            LIMIT ?
        """, (self.MIN_TASKS_FOR_SCORE, limit)).fetchall()
        
        return [
            {
                "agent_id": r["agent_id"],
                "trust_score": r["trust_score"],
                "total_tasks": r["total_tasks"],
                "success_rate": r["success_count"] / r["total_tasks"] if r["total_tasks"] else 0,
            }
            for r in rows
        ]


# Global instance
_reputation_tracker: Optional[ReputationTracker] = None


def get_reputation_tracker() -> ReputationTracker:
    """Get or create the global reputation tracker."""
    global _reputation_tracker
    if _reputation_tracker is None:
        _reputation_tracker = ReputationTracker()
    return _reputation_tracker


# Convenience functions
def record_task(agent_id: str, task_type: str, **kwargs) -> str:
    """Record the start of a task."""
    return get_reputation_tracker().record_task_start(agent_id, task_type, **kwargs)


def complete_task(task_id: str, outcome: Union[str, TaskOutcome], **kwargs) -> bool:
    """Record task completion."""
    if isinstance(outcome, str):
        outcome = TaskOutcome(outcome)
    return get_reputation_tracker().record_task_complete(task_id, outcome, **kwargs)


def rate_agent(task_id: str, rating: float, **kwargs) -> bool:
    """Rate a task."""
    return get_reputation_tracker().rate_task(task_id, rating, **kwargs)


def get_trust(agent_id: str) -> float:
    """Get an agent's trust score."""
    return get_reputation_tracker().get_trust_score(agent_id)
