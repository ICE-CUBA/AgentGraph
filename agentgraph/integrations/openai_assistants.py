"""
OpenAI Assistants Integration for AgentGraph

Automatically tracks all Assistant runs, steps, and tool calls.

Usage:
    from openai import OpenAI
    from agentgraph.integrations import OpenAIAssistantsTracker
    
    client = OpenAI()
    tracker = OpenAIAssistantsTracker(agentgraph_api_key="...")
    
    # Wrap the client
    client = tracker.wrap(client)
    
    # Use normally - all runs are now tracked!
    run = client.beta.threads.runs.create(
        thread_id="thread_...",
        assistant_id="asst_..."
    )

Alternative usage with decorator:
    from agentgraph.integrations import track_assistant_run
    
    @track_assistant_run(api_key="...")
    def my_assistant_task():
        client = OpenAI()
        # ... use assistant ...
"""

import functools
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass

try:
    from openai import OpenAI
    from openai.types.beta.threads import Run, Message
    from openai.types.beta.threads.runs import RunStep
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAI = None

from ..sdk.client import AgentGraphClient


@dataclass
class TrackedRun:
    """Tracks state for a single Assistant run."""
    run_id: str
    thread_id: str
    assistant_id: str
    start_time: float
    event_id: str
    step_count: int = 0
    tool_calls: int = 0


class OpenAIAssistantsTracker:
    """
    Tracks OpenAI Assistants runs and logs them to AgentGraph.
    
    Captures:
    - Run creation, completion, and errors
    - Individual run steps
    - Tool calls with inputs/outputs
    - Message creation
    - Token usage
    """
    
    def __init__(
        self,
        agentgraph_api_key: str,
        agentgraph_url: str = "http://localhost:8080",
        session_name: Optional[str] = None,
        log_messages: bool = True,
        log_steps: bool = True
    ):
        """
        Initialize the tracker.
        
        Args:
            agentgraph_api_key: API key from AgentGraph
            agentgraph_url: AgentGraph server URL
            session_name: Name for the tracking session
            log_messages: Whether to log message content
            log_steps: Whether to log individual run steps
        """
        if not HAS_OPENAI:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.client = AgentGraphClient(
            api_key=agentgraph_api_key,
            base_url=agentgraph_url,
            session_name=session_name or "OpenAI Assistants"
        )
        self.log_messages = log_messages
        self.log_steps = log_steps
        self._active_runs: Dict[str, TrackedRun] = {}
    
    def wrap(self, openai_client: "OpenAI") -> "OpenAI":
        """
        Wrap an OpenAI client to automatically track all Assistant operations.
        
        Args:
            openai_client: The OpenAI client instance
            
        Returns:
            The same client with tracking enabled
        """
        # Store original methods
        original_runs_create = openai_client.beta.threads.runs.create
        original_runs_create_and_poll = getattr(
            openai_client.beta.threads.runs, 
            'create_and_poll', 
            None
        )
        original_submit_tool_outputs = openai_client.beta.threads.runs.submit_tool_outputs
        
        tracker = self
        
        # Wrap runs.create
        @functools.wraps(original_runs_create)
        def tracked_runs_create(*args, **kwargs):
            run = original_runs_create(*args, **kwargs)
            tracker._on_run_created(run, kwargs)
            return run
        
        openai_client.beta.threads.runs.create = tracked_runs_create
        
        # Wrap runs.create_and_poll if it exists
        if original_runs_create_and_poll:
            @functools.wraps(original_runs_create_and_poll)
            def tracked_create_and_poll(*args, **kwargs):
                start_time = time.time()
                run = original_runs_create_and_poll(*args, **kwargs)
                tracker._on_run_completed(run, time.time() - start_time, kwargs)
                return run
            
            openai_client.beta.threads.runs.create_and_poll = tracked_create_and_poll
        
        # Wrap submit_tool_outputs
        @functools.wraps(original_submit_tool_outputs)
        def tracked_submit_tool_outputs(*args, **kwargs):
            tracker._on_tool_outputs_submitted(kwargs)
            return original_submit_tool_outputs(*args, **kwargs)
        
        openai_client.beta.threads.runs.submit_tool_outputs = tracked_submit_tool_outputs
        
        return openai_client
    
    def _on_run_created(self, run: "Run", kwargs: dict):
        """Called when a run is created."""
        event_id = self.client.log(
            event_type="action.start",
            action="assistant_run",
            description=f"Started Assistant run {run.id}",
            input_data={
                "thread_id": run.thread_id,
                "assistant_id": run.assistant_id,
                "model": run.model,
                "instructions": kwargs.get("instructions", "")[:500] if kwargs.get("instructions") else None,
                "tools": [t.type if hasattr(t, 'type') else str(t) for t in (run.tools or [])],
            },
            metadata={
                "run_id": run.id,
                "openai_run": True
            }
        )
        
        self._active_runs[run.id] = TrackedRun(
            run_id=run.id,
            thread_id=run.thread_id,
            assistant_id=run.assistant_id,
            start_time=time.time(),
            event_id=event_id
        )
    
    def _on_run_completed(self, run: "Run", duration: float, kwargs: dict):
        """Called when a run completes (via create_and_poll)."""
        tracked = self._active_runs.pop(run.id, None)
        
        status = "success" if run.status == "completed" else "error"
        error_msg = None
        
        if run.status == "failed":
            error_msg = run.last_error.message if run.last_error else "Run failed"
        elif run.status == "cancelled":
            error_msg = "Run was cancelled"
        elif run.status == "expired":
            error_msg = "Run expired"
        
        self.client.log(
            event_type="action.complete" if status == "success" else "action.error",
            action="assistant_run",
            description=f"Assistant run {run.id} {run.status}",
            output_data={
                "status": run.status,
                "usage": {
                    "prompt_tokens": run.usage.prompt_tokens if run.usage else 0,
                    "completion_tokens": run.usage.completion_tokens if run.usage else 0,
                    "total_tokens": run.usage.total_tokens if run.usage else 0,
                } if run.usage else None,
            },
            duration_ms=int(duration * 1000),
            status=status,
            error_message=error_msg,
            parent_event_id=tracked.event_id if tracked else None,
            metadata={
                "run_id": run.id,
                "step_count": tracked.step_count if tracked else 0,
                "tool_calls": tracked.tool_calls if tracked else 0,
            }
        )
    
    def _on_tool_outputs_submitted(self, kwargs: dict):
        """Called when tool outputs are submitted."""
        run_id = kwargs.get("run_id")
        tool_outputs = kwargs.get("tool_outputs", [])
        
        tracked = self._active_runs.get(run_id)
        if tracked:
            tracked.tool_calls += len(tool_outputs)
        
        self.client.log(
            event_type="tool.result",
            action="submit_tool_outputs",
            description=f"Submitted {len(tool_outputs)} tool outputs",
            output_data={
                "tool_outputs": [
                    {
                        "tool_call_id": to.get("tool_call_id"),
                        "output_preview": str(to.get("output", ""))[:200]
                    }
                    for to in tool_outputs
                ]
            },
            parent_event_id=tracked.event_id if tracked else None,
            metadata={"run_id": run_id}
        )
    
    def log_step(self, step: "RunStep"):
        """
        Manually log a run step (useful when polling steps).
        
        Args:
            step: The RunStep object from OpenAI
        """
        if not self.log_steps:
            return
        
        tracked = self._active_runs.get(step.run_id)
        if tracked:
            tracked.step_count += 1
        
        step_details = {}
        if step.step_details:
            if step.step_details.type == "message_creation":
                step_details["type"] = "message_creation"
                step_details["message_id"] = step.step_details.message_creation.message_id
            elif step.step_details.type == "tool_calls":
                step_details["type"] = "tool_calls"
                step_details["tools"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": tc.function.name if hasattr(tc, 'function') and tc.function else None
                    }
                    for tc in (step.step_details.tool_calls or [])
                ]
        
        self.client.log(
            event_type="action.complete",
            action=f"step_{step.step_details.type}" if step.step_details else "step",
            description=f"Run step {step.id}",
            output_data=step_details,
            status="success" if step.status == "completed" else "error",
            parent_event_id=tracked.event_id if tracked else None,
            metadata={
                "run_id": step.run_id,
                "step_id": step.id,
                "step_type": step.type
            }
        )
    
    def log_message(self, message: "Message", direction: str = "received"):
        """
        Log a message from the thread.
        
        Args:
            message: The Message object from OpenAI
            direction: "sent" or "received"
        """
        if not self.log_messages:
            return
        
        content = ""
        if message.content:
            for block in message.content:
                if hasattr(block, 'text') and block.text:
                    content += block.text.value
        
        self.client.log_message(
            direction=direction,
            content=content[:1000],  # Truncate long messages
            sender=message.assistant_id if message.role == "assistant" else "user"
        )


def track_assistant_run(
    api_key: str,
    base_url: str = "http://localhost:8080",
    session_name: Optional[str] = None
) -> Callable:
    """
    Decorator to track an Assistant run within a function.
    
    Usage:
        @track_assistant_run(api_key="...")
        def my_assistant_task():
            client = OpenAI()
            # ... use assistant ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = AgentGraphClient(
                api_key=api_key,
                base_url=base_url,
                session_name=session_name or f"Assistant: {func.__name__}"
            )
            
            start_time = time.time()
            start_event = client.log(
                event_type="action.start",
                action=func.__name__,
                description=f"Starting assistant task: {func.__name__}"
            )
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                client.log(
                    event_type="action.complete",
                    action=func.__name__,
                    description=f"Completed assistant task: {func.__name__}",
                    duration_ms=duration_ms,
                    status="success",
                    parent_event_id=start_event
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                client.log(
                    event_type="action.error",
                    action=func.__name__,
                    description=f"Failed assistant task: {func.__name__}",
                    duration_ms=duration_ms,
                    status="error",
                    error_message=str(e),
                    parent_event_id=start_event
                )
                raise
        
        return wrapper
    return decorator


# Streaming support for newer OpenAI SDK
class AssistantEventHandler:
    """
    Event handler for OpenAI Assistants streaming.
    
    Usage:
        from openai import OpenAI
        from agentgraph.integrations import AssistantEventHandler
        
        client = OpenAI()
        handler = AssistantEventHandler(agentgraph_api_key="...")
        
        with client.beta.threads.runs.stream(
            thread_id="...",
            assistant_id="...",
            event_handler=handler
        ) as stream:
            for text in stream.text_deltas:
                print(text, end="", flush=True)
    """
    
    def __init__(
        self,
        agentgraph_api_key: str,
        agentgraph_url: str = "http://localhost:8080"
    ):
        self.client = AgentGraphClient(
            api_key=agentgraph_api_key,
            base_url=agentgraph_url,
            session_name="OpenAI Assistants Stream"
        )
        self._run_event_id: Optional[str] = None
        self._start_time: float = 0
        self._tool_calls: List[Dict] = []
    
    def on_run_created(self, run: "Run"):
        self._start_time = time.time()
        self._run_event_id = self.client.log(
            event_type="action.start",
            action="assistant_stream",
            description=f"Started streaming run {run.id}",
            metadata={"run_id": run.id, "streaming": True}
        )
    
    def on_run_completed(self, run: "Run"):
        duration = int((time.time() - self._start_time) * 1000)
        self.client.log(
            event_type="action.complete",
            action="assistant_stream",
            description=f"Streaming run {run.id} completed",
            duration_ms=duration,
            output_data={
                "usage": {
                    "prompt_tokens": run.usage.prompt_tokens if run.usage else 0,
                    "completion_tokens": run.usage.completion_tokens if run.usage else 0,
                } if run.usage else None
            },
            parent_event_id=self._run_event_id,
            status="success"
        )
    
    def on_run_failed(self, run: "Run"):
        duration = int((time.time() - self._start_time) * 1000)
        self.client.log(
            event_type="action.error",
            action="assistant_stream",
            description=f"Streaming run {run.id} failed",
            duration_ms=duration,
            status="error",
            error_message=run.last_error.message if run.last_error else "Unknown error",
            parent_event_id=self._run_event_id
        )
    
    def on_tool_call_created(self, tool_call):
        self._tool_calls.append({
            "id": tool_call.id,
            "type": tool_call.type,
            "function": tool_call.function.name if hasattr(tool_call, 'function') else None
        })
        
        self.client.log(
            event_type="tool.call",
            action=tool_call.function.name if hasattr(tool_call, 'function') else tool_call.type,
            description=f"Tool call: {tool_call.type}",
            parent_event_id=self._run_event_id,
            metadata={"tool_call_id": tool_call.id}
        )
