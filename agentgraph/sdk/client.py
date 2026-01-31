"""
AgentGraph Python SDK

Simple SDK for logging agent activities to AgentGraph.
"""

import functools
import time
from typing import Any, Callable, Dict, List, Optional
from contextlib import contextmanager

import requests


class AgentGraphClient:
    """
    Client for logging agent activities to AgentGraph.
    
    Usage:
        client = AgentGraphClient(api_key="your-api-key")
        
        # Log a simple event
        client.log("tool.call", action="search", input_data={"query": "hello"})
        
        # Use decorator for automatic logging
        @client.track
        def my_function(x, y):
            return x + y
        
        # Use context manager for tracking duration
        with client.track_context("my_operation"):
            do_something()
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8080",
        auto_session: bool = True,
        session_name: Optional[str] = None
    ):
        """
        Initialize the AgentGraph client.
        
        Args:
            api_key: Agent API key from AgentGraph
            base_url: AgentGraph API URL
            auto_session: Automatically create a session
            session_name: Name for the auto-created session
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session_id: Optional[str] = None
        self._parent_event_id: Optional[str] = None
        
        if auto_session:
            self.session_id = self.create_session(name=session_name or "Auto Session")
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request."""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self._headers(), **kwargs)
        response.raise_for_status()
        return response.json()
    
    # ==================== Core Methods ====================
    
    def log(
        self,
        event_type: str,
        action: str = "",
        description: str = "",
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        parent_event_id: Optional[str] = None
    ) -> str:
        """
        Log an event to AgentGraph.
        
        Args:
            event_type: Type of event (e.g., "tool.call", "decision", "action.complete")
            action: Action name
            description: Human-readable description
            input_data: Input/parameters for the action
            output_data: Output/result of the action
            tags: Tags for categorization
            metadata: Additional metadata
            status: Status (success, error, pending)
            error_message: Error message if status is error
            duration_ms: Duration in milliseconds
            parent_event_id: Parent event for hierarchical tracking
        
        Returns:
            Event ID
        """
        payload = {
            "type": event_type,
            "session_id": self.session_id,
            "action": action,
            "description": description,
            "input_data": input_data,
            "output_data": output_data,
            "tags": tags or [],
            "metadata": metadata or {},
            "status": status,
            "error_message": error_message,
            "duration_ms": duration_ms,
            "parent_event_id": parent_event_id or self._parent_event_id
        }
        
        result = self._request("POST", "/events", json=payload)
        return result["id"]
    
    def log_batch(self, events: List[Dict[str, Any]]) -> List[str]:
        """
        Log multiple events at once.
        
        Args:
            events: List of event dictionaries
        
        Returns:
            List of event IDs
        """
        for event in events:
            if "session_id" not in event:
                event["session_id"] = self.session_id
        
        result = self._request("POST", "/events/batch", json={"events": events})
        return result["event_ids"]
    
    def create_session(self, name: str = "", user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session.
        
        Args:
            name: Session name
            user_id: Associated user ID
            metadata: Session metadata
        
        Returns:
            Session ID
        """
        payload = {
            "name": name,
            "user_id": user_id,
            "metadata": metadata or {}
        }
        result = self._request("POST", "/sessions", json=payload)
        return result["id"]
    
    def set_session(self, session_id: str):
        """Set the current session ID."""
        self.session_id = session_id
    
    # ==================== Entity & Relationship Methods ====================
    
    def create_entity(
        self,
        entity_type: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an entity in the graph.
        
        Args:
            entity_type: Type of entity (user, task, document, tool, resource, custom)
            name: Name of the entity
            metadata: Additional metadata
        
        Returns:
            Entity ID
        """
        payload = {
            "type": entity_type,
            "name": name,
            "metadata": metadata or {}
        }
        result = self._request("POST", "/entities", json=payload)
        return result["id"]
    
    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a relationship between entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship (created, modified, referenced, depends_on, etc.)
            metadata: Additional metadata
        
        Returns:
            Relationship ID
        """
        payload = {
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "type": relationship_type,
            "metadata": metadata or {}
        }
        result = self._request("POST", "/relationships", json=payload)
        return result["id"]
    
    # ==================== Query Methods ====================
    
    def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ask a natural language question about agent activity.
        
        Args:
            question: Natural language question like "what happened to customer X?"
            context: Optional context to help answer the question
        
        Returns:
            Dict with answer, matching events, entities, and summary
        
        Examples:
            >>> client.query("what happened to customer X?")
            >>> client.query("what tools were used?")
            >>> client.query("show me errors from today")
            >>> client.query("what did agent Y do?")
        """
        payload = {
            "question": question,
            "context": context or {}
        }
        return self._request("POST", "/query", json=payload)
    
    def search_events(
        self,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search events by keyword."""
        return self._request("GET", f"/search/events?q={query}&limit={limit}")
    
    def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search entities by name or metadata."""
        url = f"/search/entities?q={query}&limit={limit}"
        if entity_type:
            url += f"&entity_type={entity_type}"
        return self._request("GET", url)
    
    def get_entity_history(self, entity_id: str) -> Dict[str, Any]:
        """Get all events that reference an entity."""
        return self._request("GET", f"/entities/{entity_id}/history")
    
    # ==================== Sharing Methods ====================
    
    def share_connect(self) -> Dict[str, Any]:
        """
        Connect to the sharing hub for cross-agent collaboration.
        
        Returns:
            Connection info including list of connected agents
        """
        return self._request("POST", "/share/connect")
    
    def share_disconnect(self) -> Dict[str, Any]:
        """Disconnect from the sharing hub."""
        return self._request("POST", "/share/disconnect")
    
    def share_subscribe(
        self,
        topics: Optional[List[str]] = None,
        entity_ids: Optional[List[str]] = None,
        source_agent_ids: Optional[List[str]] = None
    ) -> str:
        """
        Subscribe to events from other agents.
        
        Args:
            topics: Event topics to subscribe to (e.g., "decision.made", "action.completed")
            entity_ids: Specific entities to watch
            source_agent_ids: Specific agents to watch
        
        Returns:
            Subscription ID
        """
        payload = {
            "topics": topics or [],
            "entity_ids": entity_ids or [],
            "source_agent_ids": source_agent_ids or []
        }
        result = self._request("POST", "/share/subscribe", json=payload)
        return result.get("subscription_id", "")
    
    def share_unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        result = self._request("DELETE", f"/share/subscribe/{subscription_id}")
        return result.get("success", False)
    
    def share_publish(
        self,
        topic: str = "action.completed",
        action: str = "",
        description: str = "",
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        target_agent_ids: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ) -> Dict[str, Any]:
        """
        Publish a context event to other agents.
        
        Args:
            topic: Event topic (e.g., "decision.made", "action.completed")
            action: Action name
            description: Human-readable description
            entity_id: Related entity ID
            entity_type: Type of entity
            target_agent_ids: Specific agents to send to (empty = broadcast to subscribers)
            data: Additional context data
            priority: Event priority (higher = more important)
        
        Returns:
            Event info including recipient count
        """
        payload = {
            "topic": topic,
            "action": action,
            "description": description,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "target_agent_ids": target_agent_ids or [],
            "data": data or {},
            "priority": priority
        }
        return self._request("POST", "/share/publish", json=payload)
    
    def share_get_agents(self) -> List[Dict[str, Any]]:
        """Get list of agents connected to the sharing hub."""
        result = self._request("GET", "/share/agents")
        return result.get("connected_agents", [])
    
    def share_get_events(
        self,
        agent_id: Optional[str] = None,
        topic: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent shared events."""
        params = f"?limit={limit}"
        if agent_id:
            params += f"&agent_id={agent_id}"
        if topic:
            params += f"&topic={topic}"
        if entity_id:
            params += f"&entity_id={entity_id}"
        
        result = self._request("GET", f"/share/events{params}")
        return result.get("events", [])
    
    def share_claim(self, entity_id: str) -> bool:
        """
        Claim exclusive work on an entity.
        
        Prevents other agents from claiming the same entity.
        Use for conflict prevention.
        
        Returns:
            True if claim successful
        """
        try:
            self._request("POST", f"/share/claim/{entity_id}")
            return True
        except Exception:
            return False
    
    def share_release(self, entity_id: str) -> bool:
        """Release a claim on an entity."""
        result = self._request("POST", f"/share/release/{entity_id}")
        return result.get("success", False)
    
    def share_query(self, question: str) -> Dict[str, Any]:
        """Query across all shared context."""
        return self._request("GET", f"/share/query?q={question}")
    
    # ==================== Convenience Methods ====================
    
    def log_tool_call(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """Log a tool call event."""
        return self.log(
            event_type="tool.call",
            action=tool_name,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message
        )
    
    def log_decision(
        self,
        decision: str,
        reasoning: Optional[str] = None,
        options: Optional[List[str]] = None,
        confidence: Optional[float] = None
    ) -> str:
        """Log a decision event."""
        return self.log(
            event_type="decision",
            action=decision,
            description=reasoning or "",
            metadata={
                "options": options or [],
                "confidence": confidence
            }
        )
    
    def log_message(
        self,
        direction: str,  # "sent" or "received"
        content: str,
        recipient: Optional[str] = None,
        sender: Optional[str] = None
    ) -> str:
        """Log a message event."""
        event_type = f"message.{direction}"
        return self.log(
            event_type=event_type,
            action=direction,
            description=content[:200],  # Truncate for description
            metadata={
                "content": content,
                "recipient": recipient,
                "sender": sender
            }
        )
    
    def log_error(
        self,
        error: Exception,
        action: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log an error event."""
        return self.log(
            event_type="action.error",
            action=action,
            status="error",
            error_message=str(error),
            metadata={
                "error_type": type(error).__name__,
                "context": context or {}
            }
        )
    
    # ==================== Decorators ====================
    
    def track(
        self,
        event_type: str = "action.complete",
        action: Optional[str] = None,
        log_input: bool = True,
        log_output: bool = True
    ) -> Callable:
        """
        Decorator to automatically track function calls.
        
        Usage:
            @client.track()
            def my_function(x, y):
                return x + y
            
            @client.track(event_type="tool.call", action="search")
            def search(query):
                return results
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                func_name = action or func.__name__
                
                input_data = None
                if log_input:
                    input_data = {
                        "args": [str(a)[:100] for a in args],
                        "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
                    }
                
                try:
                    result = func(*args, **kwargs)
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    output_data = None
                    if log_output and result is not None:
                        output_data = {"result": str(result)[:500]}
                    
                    self.log(
                        event_type=event_type,
                        action=func_name,
                        input_data=input_data,
                        output_data=output_data,
                        duration_ms=duration_ms,
                        status="success"
                    )
                    
                    return result
                    
                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.log(
                        event_type="action.error",
                        action=func_name,
                        input_data=input_data,
                        duration_ms=duration_ms,
                        status="error",
                        error_message=str(e)
                    )
                    raise
            
            return wrapper
        return decorator
    
    # ==================== Context Managers ====================
    
    @contextmanager
    def track_context(
        self,
        action: str,
        event_type: str = "action.complete",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracking operations with duration.
        
        Usage:
            with client.track_context("database_query"):
                results = db.query(...)
        """
        start_time = time.time()
        start_event_id = self.log(
            event_type="action.start",
            action=action,
            metadata=metadata or {}
        )
        
        # Set parent for nested events
        old_parent = self._parent_event_id
        self._parent_event_id = start_event_id
        
        try:
            yield start_event_id
            duration_ms = int((time.time() - start_time) * 1000)
            self.log(
                event_type=event_type,
                action=action,
                duration_ms=duration_ms,
                status="success",
                parent_event_id=start_event_id,
                metadata=metadata or {}
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.log(
                event_type="action.error",
                action=action,
                duration_ms=duration_ms,
                status="error",
                error_message=str(e),
                parent_event_id=start_event_id,
                metadata=metadata or {}
            )
            raise
        finally:
            self._parent_event_id = old_parent
    
    @contextmanager
    def child_context(self, parent_event_id: str):
        """
        Context manager for grouping events under a parent.
        
        Usage:
            parent_id = client.log("action.start", action="complex_task")
            with client.child_context(parent_id):
                client.log("tool.call", action="step1")
                client.log("tool.call", action="step2")
        """
        old_parent = self._parent_event_id
        self._parent_event_id = parent_event_id
        try:
            yield
        finally:
            self._parent_event_id = old_parent


# ==================== LangChain Integration ====================

class LangChainCallback:
    """
    LangChain callback handler for AgentGraph.
    
    Usage:
        from langchain.callbacks import CallbackManager
        
        client = AgentGraphClient(api_key="...")
        callback = LangChainCallback(client)
        
        llm = ChatOpenAI(callbacks=[callback])
    """
    
    def __init__(self, client: AgentGraphClient):
        self.client = client
        self._run_ids: Dict[str, str] = {}
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs):
        run_id = kwargs.get("run_id", "")
        event_id = self.client.log(
            event_type="action.start",
            action="llm_call",
            input_data={"prompts": prompts[:3]},  # Limit logged prompts
            metadata={"model": serialized.get("name", "unknown")}
        )
        self._run_ids[str(run_id)] = event_id
    
    def on_llm_end(self, response, **kwargs):
        run_id = str(kwargs.get("run_id", ""))
        parent_id = self._run_ids.pop(run_id, None)
        self.client.log(
            event_type="action.complete",
            action="llm_call",
            output_data={"generations": str(response.generations)[:500]},
            parent_event_id=parent_id,
            status="success"
        )
    
    def on_llm_error(self, error: Exception, **kwargs):
        run_id = str(kwargs.get("run_id", ""))
        parent_id = self._run_ids.pop(run_id, None)
        self.client.log(
            event_type="action.error",
            action="llm_call",
            status="error",
            error_message=str(error),
            parent_event_id=parent_id
        )
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
        run_id = kwargs.get("run_id", "")
        event_id = self.client.log(
            event_type="tool.call",
            action=serialized.get("name", "unknown_tool"),
            input_data={"input": input_str[:500]}
        )
        self._run_ids[str(run_id)] = event_id
    
    def on_tool_end(self, output: str, **kwargs):
        run_id = str(kwargs.get("run_id", ""))
        parent_id = self._run_ids.pop(run_id, None)
        self.client.log(
            event_type="tool.result",
            action="tool_complete",
            output_data={"output": output[:500]},
            parent_event_id=parent_id,
            status="success"
        )
    
    def on_tool_error(self, error: Exception, **kwargs):
        run_id = str(kwargs.get("run_id", ""))
        parent_id = self._run_ids.pop(run_id, None)
        self.client.log(
            event_type="action.error",
            action="tool_error",
            status="error",
            error_message=str(error),
            parent_event_id=parent_id
        )
