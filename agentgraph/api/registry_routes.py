"""
REST API routes for Agent Registry.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ..registry import AgentRegistry, Agent, AgentStatus, Capability
from ..registry.reputation import (
    ReputationTracker,
    TaskOutcome,
    get_reputation_tracker,
)

router = APIRouter(prefix="/registry", tags=["registry"])

# Shared registry instance (will be set by main app)
_registry: Optional[AgentRegistry] = None


def set_registry(registry: AgentRegistry):
    """Set the registry instance to use."""
    global _registry
    _registry = registry


def get_registry() -> AgentRegistry:
    """Get the registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


# === Request/Response Models ===

class CapabilityModel(BaseModel):
    name: str
    metadata: dict = {}


class RegisterAgentRequest(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    capabilities: list[CapabilityModel] = []
    endpoint: Optional[str] = None
    metadata: dict = {}


class UpdateStatusRequest(BaseModel):
    status: str  # "online", "busy", "offline"


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    capabilities: list[CapabilityModel]
    status: str
    endpoint: Optional[str]
    metadata: dict
    registered_at: str
    last_seen: str
    trust_score: float


class RegistryStatsResponse(BaseModel):
    total_agents: int
    online_agents: int
    offline_agents: int


# === Routes ===

@router.post("/agents", response_model=AgentResponse)
async def register_agent(request: RegisterAgentRequest):
    """Register a new agent or update existing."""
    import uuid
    
    registry = get_registry()
    
    agent = Agent(
        id=request.id or str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        capabilities=[Capability(c.name, c.metadata) for c in request.capabilities],
        endpoint=request.endpoint,
        metadata=request.metadata,
    )
    
    registered = registry.register(agent)
    return AgentResponse(**registered.to_dict())


@router.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """Remove an agent from the registry."""
    registry = get_registry()
    
    if not registry.unregister(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"status": "ok", "message": f"Agent {agent_id} unregistered"}


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    registry = get_registry()
    
    agent = registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(**agent.to_dict())


@router.get("/agents", response_model=list[AgentResponse])
async def discover_agents(
    capability: Optional[str] = Query(None, description="Filter by capability"),
    online_only: bool = Query(False, description="Only return online agents"),
):
    """Discover agents matching criteria."""
    registry = get_registry()
    
    agents = registry.discover(
        capability=capability,
        online_only=online_only,
    )
    
    return [AgentResponse(**a.to_dict()) for a in agents]


@router.post("/agents/{agent_id}/heartbeat")
async def heartbeat(agent_id: str):
    """Send a heartbeat to indicate agent is alive."""
    registry = get_registry()
    
    if not registry.heartbeat(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"status": "ok", "agent_id": agent_id}


@router.patch("/agents/{agent_id}/status")
async def update_status(agent_id: str, request: UpdateStatusRequest):
    """Update an agent's status."""
    registry = get_registry()
    
    try:
        status = AgentStatus(request.status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {[s.value for s in AgentStatus]}"
        )
    
    if not registry.update_status(agent_id, status):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"status": "ok", "agent_id": agent_id, "new_status": status.value}


@router.get("/stats", response_model=RegistryStatsResponse)
async def get_stats():
    """Get registry statistics."""
    registry = get_registry()
    
    total = registry.count()
    online = registry.count(online_only=True)
    
    return RegistryStatsResponse(
        total_agents=total,
        online_agents=online,
        offline_agents=total - online,
    )


@router.post("/cleanup")
async def cleanup_stale():
    """Mark stale agents as offline."""
    registry = get_registry()
    
    count = registry.cleanup_stale()
    
    return {"status": "ok", "agents_marked_offline": count}


# ==================== Reputation Routes ====================

class RecordTaskRequest(BaseModel):
    agent_id: str
    task_type: str
    task_id: Optional[str] = None
    metadata: dict = {}


class CompleteTaskRequest(BaseModel):
    outcome: str  # "success", "failure", "timeout", "partial"
    error_message: Optional[str] = None


class RateTaskRequest(BaseModel):
    rating: float  # 0.0 to 1.0
    rated_by: Optional[str] = None


class AgentStatsResponse(BaseModel):
    agent_id: str
    total_tasks: int
    success_count: Optional[int] = None
    failure_count: Optional[int] = None
    success_rate: float
    avg_duration_ms: Optional[float] = None
    avg_rating: Optional[float] = None
    trust_score: float


@router.post("/tasks/start")
async def start_task(request: RecordTaskRequest):
    """Record the start of a task."""
    tracker = get_reputation_tracker()
    
    task_id = tracker.record_task_start(
        agent_id=request.agent_id,
        task_type=request.task_type,
        task_id=request.task_id,
        metadata=request.metadata,
    )
    
    return {"task_id": task_id, "status": "started"}


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, request: CompleteTaskRequest):
    """Record task completion."""
    tracker = get_reputation_tracker()
    
    try:
        outcome = TaskOutcome(request.outcome)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outcome. Must be one of: {[o.value for o in TaskOutcome]}"
        )
    
    success = tracker.record_task_complete(
        task_id=task_id,
        outcome=outcome,
        error_message=request.error_message,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"task_id": task_id, "status": "completed", "outcome": outcome.value}


@router.post("/tasks/{task_id}/rate")
async def rate_task(task_id: str, request: RateTaskRequest):
    """Rate a completed task."""
    tracker = get_reputation_tracker()
    
    success = tracker.rate_task(
        task_id=task_id,
        rating=request.rating,
        rated_by=request.rated_by,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"task_id": task_id, "rating": request.rating}


@router.get("/agents/{agent_id}/reputation", response_model=AgentStatsResponse)
async def get_agent_reputation(agent_id: str):
    """Get reputation and statistics for an agent."""
    tracker = get_reputation_tracker()
    stats = tracker.get_agent_stats(agent_id)
    return AgentStatsResponse(**stats)


@router.get("/agents/{agent_id}/trust")
async def get_agent_trust(agent_id: str):
    """Get just the trust score for an agent."""
    tracker = get_reputation_tracker()
    score = tracker.get_trust_score(agent_id)
    return {"agent_id": agent_id, "trust_score": score}


@router.get("/leaderboard")
async def get_leaderboard(limit: int = Query(10, ge=1, le=100)):
    """Get top agents by trust score."""
    tracker = get_reputation_tracker()
    leaderboard = tracker.get_leaderboard(limit=limit)
    return {"leaderboard": leaderboard, "count": len(leaderboard)}
