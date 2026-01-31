"""
Tests for Trust & Reputation System.
"""

import pytest
import tempfile
import os
from pathlib import Path

from agentgraph.registry.reputation import (
    ReputationTracker,
    TaskOutcome,
    record_task,
    complete_task,
    rate_agent,
    get_trust,
)


@pytest.fixture
def temp_tracker():
    """Create a reputation tracker with a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    tracker = ReputationTracker(db_path=db_path)
    yield tracker
    
    # Cleanup
    os.unlink(db_path)


class TestReputationTracker:
    """Test ReputationTracker."""
    
    def test_record_and_complete_task(self, temp_tracker):
        """Test basic task recording."""
        task_id = temp_tracker.record_task_start(
            agent_id="agent-1",
            task_type="translate"
        )
        
        assert task_id is not None
        
        result = temp_tracker.record_task_complete(task_id, TaskOutcome.SUCCESS)
        assert result is True
    
    def test_task_not_found(self, temp_tracker):
        """Test completing non-existent task."""
        result = temp_tracker.record_task_complete("fake-task", TaskOutcome.SUCCESS)
        assert result is False
    
    def test_rate_task(self, temp_tracker):
        """Test rating a task."""
        task_id = temp_tracker.record_task_start("agent-1", "search")
        temp_tracker.record_task_complete(task_id, TaskOutcome.SUCCESS)
        
        result = temp_tracker.rate_task(task_id, 0.9, rated_by="agent-2")
        assert result is True
    
    def test_trust_score_calculation(self, temp_tracker):
        """Test trust score calculation."""
        agent_id = "reliable-agent"
        
        # Complete several successful tasks
        for i in range(10):
            task_id = temp_tracker.record_task_start(agent_id, "task")
            temp_tracker.record_task_complete(task_id, TaskOutcome.SUCCESS)
            temp_tracker.rate_task(task_id, 0.9)
        
        score = temp_tracker.get_trust_score(agent_id)
        assert score > 0.5  # Should be above average
        
        stats = temp_tracker.get_agent_stats(agent_id)
        assert stats["total_tasks"] == 10
        assert stats["success_rate"] == 1.0
    
    def test_trust_score_decreases_on_failures(self, temp_tracker):
        """Test that failures decrease trust score."""
        good_agent = "good-agent"
        bad_agent = "bad-agent"
        
        # Good agent: all successes
        for i in range(5):
            task_id = temp_tracker.record_task_start(good_agent, "task")
            temp_tracker.record_task_complete(task_id, TaskOutcome.SUCCESS)
        
        # Bad agent: all failures
        for i in range(5):
            task_id = temp_tracker.record_task_start(bad_agent, "task")
            temp_tracker.record_task_complete(task_id, TaskOutcome.FAILURE)
        
        good_score = temp_tracker.get_trust_score(good_agent)
        bad_score = temp_tracker.get_trust_score(bad_agent)
        
        assert good_score > bad_score
    
    def test_leaderboard(self, temp_tracker):
        """Test leaderboard generation."""
        # Create agents with varying performance
        for i in range(3):
            agent_id = f"agent-{i}"
            # More tasks = higher on leaderboard (if successful)
            for j in range(5 + i * 2):
                task_id = temp_tracker.record_task_start(agent_id, "task")
                temp_tracker.record_task_complete(task_id, TaskOutcome.SUCCESS)
        
        leaderboard = temp_tracker.get_leaderboard(limit=10)
        
        # Should have 3 agents (all with >= 5 tasks)
        assert len(leaderboard) == 3
        
        # Should be sorted by trust score
        scores = [entry["trust_score"] for entry in leaderboard]
        assert scores == sorted(scores, reverse=True)
    
    def test_default_trust_score(self, temp_tracker):
        """Test that new agents have neutral trust score."""
        score = temp_tracker.get_trust_score("new-agent")
        assert score == 0.5  # Neutral default
    
    def test_rating_clamped(self, temp_tracker):
        """Test that ratings are clamped to [0, 1]."""
        task_id = temp_tracker.record_task_start("agent", "task")
        temp_tracker.record_task_complete(task_id, TaskOutcome.SUCCESS)
        
        # Rating > 1 should be clamped
        result = temp_tracker.rate_task(task_id, 1.5)
        assert result is True
        
        # Rating < 0 should be clamped
        task_id2 = temp_tracker.record_task_start("agent", "task2")
        temp_tracker.record_task_complete(task_id2, TaskOutcome.SUCCESS)
        result = temp_tracker.rate_task(task_id2, -0.5)
        assert result is True


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_record_and_complete(self):
        """Test convenience functions."""
        task_id = record_task("test-agent", "test-task")
        assert task_id is not None
        
        result = complete_task(task_id, "success")
        assert result is True
    
    def test_get_trust(self):
        """Test get_trust convenience function."""
        score = get_trust("some-agent")
        assert 0 <= score <= 1
