"""
AgentGraph Easy Mode

The simplest possible interface. Zero configuration.

Usage:
    from agentgraph.easy import log, query, connect
    
    # That's it. No server setup, no API keys, no config.
    log("searched for AI papers")
    log("decided to use GPT-4", type="decision")
    
    results = query("what did I do today?")
    
    # For multi-agent:
    connect("MyAgent")
    share("found 3 relevant papers", topic="research")
"""

import atexit
import os
import subprocess
import sys
import time
import threading
from typing import Any, Dict, List, Optional

import requests

# Global state for easy mode
_server_process = None
_api_key = None
_base_url = "http://localhost:8080"
_agent_name = "default"
_initialized = False
_init_lock = threading.Lock()


def _ensure_server():
    """Start server if not running."""
    global _server_process
    
    try:
        r = requests.get(f"{_base_url}/health", timeout=1)
        if r.status_code == 200:
            return True
    except Exception:
        pass
    
    # Start server in background
    _server_process = subprocess.Popen(
        [sys.executable, "-m", "agentgraph.api.server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for it to start
    for _ in range(30):
        try:
            r = requests.get(f"{_base_url}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.1)
    
    return False


def _ensure_agent():
    """Create default agent if needed."""
    global _api_key, _agent_name
    
    if _api_key:
        return
    
    # Check for env var first
    _api_key = os.environ.get("AGENTGRAPH_API_KEY")
    if _api_key:
        return
    
    # Create a default agent
    try:
        r = requests.post(f"{_base_url}/agents", json={
            "name": _agent_name,
            "platform": "easy_mode"
        })
        if r.status_code == 200:
            _api_key = r.json().get("api_key")
    except Exception:
        pass


def _init():
    """Initialize easy mode."""
    global _initialized
    
    with _init_lock:
        if _initialized:
            return
        
        _ensure_server()
        _ensure_agent()
        _initialized = True


def _cleanup():
    """Cleanup on exit."""
    global _server_process
    if _server_process:
        _server_process.terminate()
        _server_process = None


atexit.register(_cleanup)


# ==================== Simple API ====================

def log(
    action: str,
    type: str = "action.complete",
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    Log something the agent did. Simplest possible interface.
    
    Args:
        action: What happened (e.g., "searched for AI papers")
        type: Event type (default: "action.complete")
        data: Optional additional data
        
    Returns:
        Event ID
        
    Examples:
        log("started research")
        log("called OpenAI API", type="tool.call", data={"model": "gpt-4"})
        log("decided to use approach A", type="decision")
    """
    _init()
    
    try:
        r = requests.post(
            f"{_base_url}/events",
            headers={"X-API-Key": _api_key} if _api_key else {},
            json={
                "type": type,
                "action": action,
                "description": kwargs.get("description", action),
                "input_data": data,
                "metadata": kwargs
            }
        )
        if r.status_code == 200:
            return r.json().get("id", "")
    except Exception as e:
        print(f"AgentGraph: {e}")
    
    return ""


def query(question: str) -> Dict[str, Any]:
    """
    Ask a question about what happened.
    
    Args:
        question: Natural language question
        
    Returns:
        Answer with matching events
        
    Examples:
        query("what did I do today?")
        query("what tools were used?")
        query("show me errors")
    """
    _init()
    
    try:
        r = requests.post(
            f"{_base_url}/query",
            json={"question": question}
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"AgentGraph: {e}")
    
    return {"answer": "Unable to query", "events": []}


def search(text: str, limit: int = 10) -> List[Dict]:
    """
    Search for events matching text.
    
    Args:
        text: Search query
        limit: Max results
        
    Returns:
        List of matching events
    """
    _init()
    
    try:
        r = requests.get(f"{_base_url}/search/events", params={"q": text, "limit": limit})
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    
    return []


def connect(agent_name: str = "default") -> bool:
    """
    Connect as a named agent (for multi-agent scenarios).
    
    Args:
        agent_name: Your agent's name
        
    Returns:
        True if connected
    """
    global _agent_name, _api_key, _initialized
    
    _agent_name = agent_name
    _api_key = None
    _initialized = False
    _init()
    
    # Connect to sharing hub
    try:
        r = requests.post(
            f"{_base_url}/share/connect",
            headers={"X-API-Key": _api_key} if _api_key else {}
        )
        return r.status_code == 200
    except Exception:
        return False


def share(
    message: str,
    topic: str = "action.completed",
    data: Optional[Dict] = None
) -> int:
    """
    Share something with other agents.
    
    Args:
        message: What to share
        topic: Event topic
        data: Additional data
        
    Returns:
        Number of agents that received it
    """
    _init()
    
    try:
        r = requests.post(
            f"{_base_url}/share/publish",
            headers={"X-API-Key": _api_key} if _api_key else {},
            json={
                "topic": topic,
                "action": message[:50],
                "description": message,
                "data": data or {}
            }
        )
        if r.status_code == 200:
            return r.json().get("recipient_count", 0)
    except Exception:
        pass
    
    return 0


def entity(name: str, type: str = "custom", **metadata) -> str:
    """
    Create an entity in the knowledge graph.
    
    Args:
        name: Entity name
        type: Entity type (user, task, document, tool, resource, custom)
        **metadata: Additional properties
        
    Returns:
        Entity ID
    """
    _init()
    
    try:
        r = requests.post(
            f"{_base_url}/entities",
            headers={"X-API-Key": _api_key} if _api_key else {},
            json={"name": name, "type": type, "metadata": metadata}
        )
        if r.status_code == 200:
            return r.json().get("id", "")
    except Exception:
        pass
    
    return ""


def link(from_id: str, to_id: str, type: str = "referenced") -> str:
    """
    Create a relationship between entities.
    
    Args:
        from_id: Source entity ID
        to_id: Target entity ID
        type: Relationship type
        
    Returns:
        Relationship ID
    """
    _init()
    
    try:
        r = requests.post(
            f"{_base_url}/relationships",
            headers={"X-API-Key": _api_key} if _api_key else {},
            json={
                "source_entity_id": from_id,
                "target_entity_id": to_id,
                "type": type
            }
        )
        if r.status_code == 200:
            return r.json().get("id", "")
    except Exception:
        pass
    
    return ""


# ==================== Even Simpler: Decorators ====================

def track(fn):
    """
    Decorator to automatically track function calls.
    
    Example:
        @track
        def my_function(x):
            return x * 2
    """
    def wrapper(*args, **kwargs):
        _init()
        start = time.time()
        try:
            result = fn(*args, **kwargs)
            duration = int((time.time() - start) * 1000)
            log(fn.__name__, type="tool.call", data={
                "args": str(args)[:100],
                "result": str(result)[:100],
                "duration_ms": duration
            })
            return result
        except Exception as e:
            log(fn.__name__, type="action.error", data={"error": str(e)})
            raise
    
    wrapper.__name__ = fn.__name__
    return wrapper
