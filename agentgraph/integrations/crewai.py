"""
CrewAI Integration for AgentGraph

Automatically tracks all CrewAI agent activities, tasks, and crew operations.

Usage:
    from crewai import Agent, Task, Crew
    from agentgraph.integrations import CrewAITracker
    
    tracker = CrewAITracker(agentgraph_api_key="...")
    
    # Wrap your crew
    crew = Crew(agents=[...], tasks=[...])
    crew = tracker.wrap(crew)
    
    # Run normally - all activities are tracked!
    result = crew.kickoff()

Alternative - wrap individual agents:
    agent = Agent(role="Researcher", ...)
    agent = tracker.wrap_agent(agent)
"""

import functools
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

try:
    from crewai import Agent, Task, Crew
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False
    Agent = None
    Task = None
    Crew = None

from ..sdk.client import AgentGraphClient


@dataclass
class TrackedTask:
    """Tracks state for a CrewAI task."""
    task_id: str
    description: str
    agent_role: str
    start_time: float
    event_id: str


@dataclass 
class TrackedCrew:
    """Tracks state for a CrewAI crew run."""
    crew_id: str
    start_time: float
    event_id: str
    tasks_completed: int = 0
    agents: List[str] = field(default_factory=list)


class CrewAITracker:
    """
    Tracks CrewAI crew operations and logs them to AgentGraph.
    
    Captures:
    - Crew kickoff and completion
    - Individual task execution
    - Agent actions and tool usage
    - Inter-agent delegation
    - Task outputs
    """
    
    def __init__(
        self,
        agentgraph_api_key: str,
        agentgraph_url: str = "http://localhost:8080",
        session_name: Optional[str] = None,
        log_agent_thoughts: bool = True,
        log_tool_calls: bool = True
    ):
        """
        Initialize the tracker.
        
        Args:
            agentgraph_api_key: API key from AgentGraph
            agentgraph_url: AgentGraph server URL
            session_name: Name for the tracking session
            log_agent_thoughts: Whether to log agent reasoning
            log_tool_calls: Whether to log individual tool calls
        """
        if not HAS_CREWAI:
            raise ImportError("crewai package not installed. Run: pip install crewai")
        
        self.client = AgentGraphClient(
            api_key=agentgraph_api_key,
            base_url=agentgraph_url,
            session_name=session_name or "CrewAI"
        )
        self.log_agent_thoughts = log_agent_thoughts
        self.log_tool_calls = log_tool_calls
        self._active_crews: Dict[str, TrackedCrew] = {}
        self._active_tasks: Dict[str, TrackedTask] = {}
        self._agent_entities: Dict[str, str] = {}  # role -> entity_id
    
    def wrap(self, crew: "Crew") -> "Crew":
        """
        Wrap a Crew to automatically track all operations.
        
        Args:
            crew: The CrewAI Crew instance
            
        Returns:
            The same crew with tracking enabled
        """
        tracker = self
        original_kickoff = crew.kickoff
        
        # Create entities for all agents
        for agent in crew.agents:
            entity_id = self.client.create_entity(
                entity_type="agent",
                name=agent.role,
                metadata={
                    "goal": agent.goal,
                    "backstory": agent.backstory[:200] if agent.backstory else None,
                    "framework": "crewai"
                }
            )
            self._agent_entities[agent.role] = entity_id
        
        @functools.wraps(original_kickoff)
        def tracked_kickoff(*args, **kwargs):
            crew_id = f"crew_{int(time.time())}"
            start_time = time.time()
            
            # Log crew start
            event_id = tracker.client.log(
                event_type="action.start",
                action="crew_kickoff",
                description=f"Starting CrewAI crew with {len(crew.agents)} agents",
                input_data={
                    "agents": [a.role for a in crew.agents],
                    "tasks": [t.description[:100] for t in crew.tasks],
                    "process": str(crew.process) if hasattr(crew, 'process') else "sequential"
                },
                metadata={"crew_id": crew_id, "crewai": True}
            )
            
            tracker._active_crews[crew_id] = TrackedCrew(
                crew_id=crew_id,
                start_time=start_time,
                event_id=event_id,
                agents=[a.role for a in crew.agents]
            )
            
            # Wrap task execution
            for task in crew.tasks:
                tracker._wrap_task(task, crew_id)
            
            try:
                result = original_kickoff(*args, **kwargs)
                duration = int((time.time() - start_time) * 1000)
                
                tracked = tracker._active_crews.pop(crew_id, None)
                
                # Log crew completion
                tracker.client.log(
                    event_type="action.complete",
                    action="crew_kickoff",
                    description="CrewAI crew completed successfully",
                    output_data={
                        "result_preview": str(result)[:500] if result else None,
                        "tasks_completed": tracked.tasks_completed if tracked else 0
                    },
                    duration_ms=duration,
                    status="success",
                    parent_event_id=event_id,
                    metadata={"crew_id": crew_id}
                )
                
                return result
                
            except Exception as e:
                duration = int((time.time() - start_time) * 1000)
                tracker._active_crews.pop(crew_id, None)
                
                tracker.client.log(
                    event_type="action.error",
                    action="crew_kickoff",
                    description=f"CrewAI crew failed: {str(e)[:100]}",
                    duration_ms=duration,
                    status="error",
                    error_message=str(e),
                    parent_event_id=event_id,
                    metadata={"crew_id": crew_id}
                )
                raise
        
        crew.kickoff = tracked_kickoff
        return crew
    
    def _wrap_task(self, task: "Task", crew_id: str):
        """Wrap a task to track its execution."""
        tracker = self
        
        # Store original execute if it exists
        if hasattr(task, '_execute_core'):
            original_execute = task._execute_core
        elif hasattr(task, 'execute'):
            original_execute = task.execute
        else:
            return  # Can't wrap this task
        
        @functools.wraps(original_execute)
        def tracked_execute(*args, **kwargs):
            task_id = f"task_{int(time.time() * 1000)}"
            start_time = time.time()
            
            agent_role = task.agent.role if task.agent else "Unknown"
            
            # Log task start
            event_id = tracker.client.log(
                event_type="action.start",
                action="task_execution",
                description=f"Agent '{agent_role}' starting task",
                input_data={
                    "task": task.description[:300],
                    "expected_output": task.expected_output[:200] if task.expected_output else None,
                    "agent": agent_role
                },
                metadata={
                    "crew_id": crew_id,
                    "task_id": task_id
                }
            )
            
            tracker._active_tasks[task_id] = TrackedTask(
                task_id=task_id,
                description=task.description[:100],
                agent_role=agent_role,
                start_time=start_time,
                event_id=event_id
            )
            
            try:
                result = original_execute(*args, **kwargs)
                duration = int((time.time() - start_time) * 1000)
                
                tracker._active_tasks.pop(task_id, None)  # Clean up
                tracked_crew = tracker._active_crews.get(crew_id)
                if tracked_crew:
                    tracked_crew.tasks_completed += 1
                
                # Log task completion
                tracker.client.log(
                    event_type="action.complete",
                    action="task_execution",
                    description=f"Agent '{agent_role}' completed task",
                    output_data={
                        "output_preview": str(result)[:500] if result else None
                    },
                    duration_ms=duration,
                    status="success",
                    parent_event_id=event_id,
                    metadata={
                        "crew_id": crew_id,
                        "task_id": task_id,
                        "agent": agent_role
                    }
                )
                
                return result
                
            except Exception as e:
                duration = int((time.time() - start_time) * 1000)
                tracker._active_tasks.pop(task_id, None)
                
                tracker.client.log(
                    event_type="action.error",
                    action="task_execution",
                    description=f"Agent '{agent_role}' failed task: {str(e)[:100]}",
                    duration_ms=duration,
                    status="error",
                    error_message=str(e),
                    parent_event_id=event_id,
                    metadata={
                        "crew_id": crew_id,
                        "task_id": task_id,
                        "agent": agent_role
                    }
                )
                raise
        
        if hasattr(task, '_execute_core'):
            task._execute_core = tracked_execute
        else:
            task.execute = tracked_execute
    
    def wrap_agent(self, agent: "Agent") -> "Agent":
        """
        Wrap an individual agent to track its activities.
        
        Args:
            agent: The CrewAI Agent instance
            
        Returns:
            The same agent with tracking enabled
        """
        # Create entity for this agent
        entity_id = self.client.create_entity(
            entity_type="agent",
            name=agent.role,
            metadata={
                "goal": agent.goal,
                "backstory": agent.backstory[:200] if agent.backstory else None,
                "framework": "crewai"
            }
        )
        self._agent_entities[agent.role] = entity_id
        
        # Could wrap agent's execute_task method here for more granular tracking
        return agent
    
    def log_delegation(
        self,
        from_agent: str,
        to_agent: str,
        task_description: str,
        context: Optional[str] = None
    ):
        """
        Log a delegation event between agents.
        
        Args:
            from_agent: Role of delegating agent
            to_agent: Role of receiving agent
            task_description: What's being delegated
            context: Additional context
        """
        # Create relationship between agents
        from_entity = self._agent_entities.get(from_agent)
        to_entity = self._agent_entities.get(to_agent)
        
        if from_entity and to_entity:
            self.client.create_relationship(
                source_id=from_entity,
                target_id=to_entity,
                relationship_type="delegated_to",
                metadata={"task": task_description[:100]}
            )
        
        self.client.log(
            event_type="action.complete",
            action="delegation",
            description=f"'{from_agent}' delegated to '{to_agent}'",
            input_data={
                "task": task_description[:300],
                "context": context[:200] if context else None
            },
            metadata={
                "from_agent": from_agent,
                "to_agent": to_agent
            }
        )
    
    def log_tool_use(
        self,
        agent_role: str,
        tool_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Any] = None,
        duration_ms: Optional[int] = None
    ):
        """
        Log a tool usage by an agent.
        
        Args:
            agent_role: Role of the agent using the tool
            tool_name: Name of the tool
            input_data: Tool input
            output_data: Tool output
            duration_ms: Duration of tool execution
        """
        if not self.log_tool_calls:
            return
        
        self.client.log(
            event_type="tool.call",
            action=tool_name,
            description=f"Agent '{agent_role}' used tool '{tool_name}'",
            input_data=input_data,
            output_data={"result": str(output_data)[:500]} if output_data else None,
            duration_ms=duration_ms,
            metadata={"agent": agent_role}
        )


# Callback-based tracking (alternative approach)
class CrewAICallback:
    """
    Callback handler for CrewAI that logs to AgentGraph.
    
    Usage with CrewAI's callback system (if supported):
        callback = CrewAICallback(agentgraph_api_key="...")
        crew = Crew(..., callbacks=[callback])
    """
    
    def __init__(
        self,
        agentgraph_api_key: str,
        agentgraph_url: str = "http://localhost:8080"
    ):
        self.client = AgentGraphClient(
            api_key=agentgraph_api_key,
            base_url=agentgraph_url,
            session_name="CrewAI Callbacks"
        )
    
    def on_crew_start(self, crew: "Crew"):
        """Called when crew starts."""
        self.client.log(
            event_type="action.start",
            action="crew_start",
            description=f"Crew started with {len(crew.agents)} agents",
            input_data={"agents": [a.role for a in crew.agents]}
        )
    
    def on_crew_end(self, crew: "Crew", output: Any):
        """Called when crew completes."""
        self.client.log(
            event_type="action.complete",
            action="crew_end",
            description="Crew completed",
            output_data={"result": str(output)[:500]}
        )
    
    def on_task_start(self, task: "Task"):
        """Called when task starts."""
        self.client.log(
            event_type="action.start",
            action="task_start",
            description=f"Task started: {task.description[:100]}",
            metadata={"agent": task.agent.role if task.agent else None}
        )
    
    def on_task_end(self, task: "Task", output: Any):
        """Called when task completes."""
        self.client.log(
            event_type="action.complete",
            action="task_end",
            description=f"Task completed: {task.description[:100]}",
            output_data={"result": str(output)[:500]}
        )
    
    def on_agent_action(self, agent: "Agent", action: str, input_data: Any):
        """Called when agent takes an action."""
        self.client.log(
            event_type="action.complete",
            action=action,
            description=f"Agent '{agent.role}' action: {action}",
            input_data={"input": str(input_data)[:300]} if input_data else None
        )
    
    def on_tool_use(self, agent: "Agent", tool: str, input_data: Any, output: Any):
        """Called when agent uses a tool."""
        self.client.log(
            event_type="tool.call",
            action=tool,
            description=f"Agent '{agent.role}' used tool: {tool}",
            input_data={"input": str(input_data)[:300]} if input_data else None,
            output_data={"output": str(output)[:300]} if output else None
        )
