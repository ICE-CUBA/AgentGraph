"""
AgentGraph API Server

FastAPI-based REST API for agent activity tracking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..core.schema import Agent, Entity, Event, EventType, EntityType, Relationship, RelationType, Session
from ..storage.database import Database

# Initialize FastAPI app
app = FastAPI(
    title="AgentGraph API",
    description="Track and visualize AI agent activities",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance
db = Database()


# ==================== Pydantic Models ====================

class AgentCreate(BaseModel):
    name: str
    platform: str = ""
    owner_id: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    capabilities: List[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    id: str
    name: str
    platform: str
    owner_id: Optional[str]
    api_key: str
    config: Dict[str, Any]
    capabilities: List[str]
    is_active: bool
    last_seen: Optional[str]
    created_at: str


class EventCreate(BaseModel):
    type: str = "custom"
    session_id: Optional[str] = None
    action: str = ""
    description: str = ""
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    parent_event_id: Optional[str] = None
    related_entity_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = "success"
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


class EventResponse(BaseModel):
    id: str
    type: str
    agent_id: str
    user_id: Optional[str]
    session_id: Optional[str]
    action: str
    description: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    parent_event_id: Optional[str]
    related_entity_ids: List[str]
    tags: List[str]
    metadata: Dict[str, Any]
    status: str
    error_message: Optional[str]
    timestamp: str
    duration_ms: Optional[int]


class EntityCreate(BaseModel):
    type: str = "custom"
    name: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionCreate(BaseModel):
    name: str = ""
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchEventCreate(BaseModel):
    events: List[EventCreate]


# ==================== Auth Dependency ====================

async def get_agent_from_api_key(x_api_key: str = Header(...)) -> Agent:
    """Authenticate agent by API key."""
    agent = db.get_agent_by_api_key(x_api_key)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key")
    db.update_agent_last_seen(agent.id)
    return agent


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


# ==================== Agent Endpoints ====================

@app.post("/agents", response_model=AgentResponse)
async def create_agent(agent_data: AgentCreate):
    """Register a new agent. Returns API key for authentication."""
    agent = Agent(
        name=agent_data.name,
        platform=agent_data.platform,
        owner_id=agent_data.owner_id,
        config=agent_data.config,
        capabilities=agent_data.capabilities
    )
    db.create_agent(agent)
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        platform=agent.platform,
        owner_id=agent.owner_id,
        api_key=agent.api_key,
        config=agent.config,
        capabilities=agent.capabilities,
        is_active=agent.is_active,
        last_seen=agent.last_seen.isoformat() if agent.last_seen else None,
        created_at=agent.created_at.isoformat()
    )


@app.get("/agents", response_model=List[AgentResponse])
async def list_agents(owner_id: Optional[str] = None):
    """List all registered agents."""
    agents = db.list_agents(owner_id=owner_id)
    return [
        AgentResponse(
            id=a.id,
            name=a.name,
            platform=a.platform,
            owner_id=a.owner_id,
            api_key=a.api_key,
            config=a.config,
            capabilities=a.capabilities,
            is_active=a.is_active,
            last_seen=a.last_seen.isoformat() if a.last_seen else None,
            created_at=a.created_at.isoformat()
        )
        for a in agents
    ]


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.to_dict()


@app.get("/agents/{agent_id}/stats")
async def get_agent_stats(agent_id: str):
    """Get agent statistics."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db.get_agent_stats(agent_id)


# ==================== Event Endpoints ====================

@app.post("/events", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    agent: Agent = Depends(get_agent_from_api_key)
):
    """Log a new event."""
    event = Event(
        type=EventType(event_data.type) if event_data.type in [e.value for e in EventType] else EventType.CUSTOM,
        agent_id=agent.id,
        session_id=event_data.session_id,
        action=event_data.action,
        description=event_data.description,
        input_data=event_data.input_data,
        output_data=event_data.output_data,
        parent_event_id=event_data.parent_event_id,
        related_entity_ids=event_data.related_entity_ids,
        tags=event_data.tags,
        metadata=event_data.metadata,
        status=event_data.status,
        error_message=event_data.error_message,
        duration_ms=event_data.duration_ms
    )
    db.create_event(event)
    return EventResponse(
        id=event.id,
        type=event.type.value,
        agent_id=event.agent_id,
        user_id=event.user_id,
        session_id=event.session_id,
        action=event.action,
        description=event.description,
        input_data=event.input_data,
        output_data=event.output_data,
        parent_event_id=event.parent_event_id,
        related_entity_ids=event.related_entity_ids,
        tags=event.tags,
        metadata=event.metadata,
        status=event.status,
        error_message=event.error_message,
        timestamp=event.timestamp.isoformat(),
        duration_ms=event.duration_ms
    )


@app.post("/events/batch")
async def create_events_batch(
    batch: BatchEventCreate,
    agent: Agent = Depends(get_agent_from_api_key)
):
    """Log multiple events at once."""
    created_events = []
    for event_data in batch.events:
        event = Event(
            type=EventType(event_data.type) if event_data.type in [e.value for e in EventType] else EventType.CUSTOM,
            agent_id=agent.id,
            session_id=event_data.session_id,
            action=event_data.action,
            description=event_data.description,
            input_data=event_data.input_data,
            output_data=event_data.output_data,
            parent_event_id=event_data.parent_event_id,
            related_entity_ids=event_data.related_entity_ids,
            tags=event_data.tags,
            metadata=event_data.metadata,
            status=event_data.status,
            error_message=event_data.error_message,
            duration_ms=event_data.duration_ms
        )
        db.create_event(event)
        created_events.append(event.id)
    
    return {"created": len(created_events), "event_ids": created_events}


@app.get("/events", response_model=List[EventResponse])
async def list_events(
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List events with optional filters."""
    events = db.list_events(
        agent_id=agent_id,
        session_id=session_id,
        event_type=event_type,
        limit=limit,
        offset=offset
    )
    return [
        EventResponse(
            id=e.id,
            type=e.type.value,
            agent_id=e.agent_id,
            user_id=e.user_id,
            session_id=e.session_id,
            action=e.action,
            description=e.description,
            input_data=e.input_data,
            output_data=e.output_data,
            parent_event_id=e.parent_event_id,
            related_entity_ids=e.related_entity_ids,
            tags=e.tags,
            metadata=e.metadata,
            status=e.status,
            error_message=e.error_message,
            timestamp=e.timestamp.isoformat(),
            duration_ms=e.duration_ms
        )
        for e in events
    ]


@app.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get event details."""
    event = db.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


# ==================== Session Endpoints ====================

@app.post("/sessions")
async def create_session(
    session_data: SessionCreate,
    agent: Agent = Depends(get_agent_from_api_key)
):
    """Create a new session."""
    session = Session(
        agent_id=agent.id,
        user_id=session_data.user_id,
        name=session_data.name,
        metadata=session_data.metadata
    )
    db.create_session(session)
    return session.to_dict()


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@app.get("/sessions/{session_id}/events")
async def get_session_events(session_id: str, limit: int = 100, offset: int = 0):
    """Get all events for a session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    events = db.list_events(session_id=session_id, limit=limit, offset=offset)
    return [e.to_dict() for e in events]


# ==================== Entity Endpoints ====================

@app.post("/entities")
async def create_entity(
    entity_data: EntityCreate,
    agent: Agent = Depends(get_agent_from_api_key)
):
    """Create a new entity."""
    entity = Entity(
        type=EntityType(entity_data.type) if entity_data.type in [e.value for e in EntityType] else EntityType.CUSTOM,
        name=entity_data.name,
        metadata=entity_data.metadata
    )
    db.create_entity(entity)
    return entity.to_dict()


@app.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Get entity details."""
    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity.to_dict()


@app.get("/entities/{entity_id}/relationships")
async def get_entity_relationships(entity_id: str, direction: str = "both"):
    """Get relationships for an entity."""
    entity = db.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    relationships = db.get_relationships(entity_id, direction=direction)
    return [r.to_dict() for r in relationships]


# ==================== Graph Query Endpoints ====================

@app.get("/graph/timeline")
async def get_timeline(
    agent_id: Optional[str] = None,
    hours: int = 24,
    limit: int = 1000
):
    """Get timeline of events for visualization."""
    events = db.list_events(agent_id=agent_id, limit=limit)
    
    # Group by hour for visualization
    timeline = {}
    for event in events:
        hour_key = event.timestamp.strftime("%Y-%m-%d %H:00")
        if hour_key not in timeline:
            timeline[hour_key] = {"count": 0, "types": {}}
        timeline[hour_key]["count"] += 1
        event_type = event.type.value
        timeline[hour_key]["types"][event_type] = timeline[hour_key]["types"].get(event_type, 0) + 1
    
    return {"timeline": timeline, "total_events": len(events)}


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
