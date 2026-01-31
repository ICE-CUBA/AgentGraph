"""
Tests for Easy Mode (zero-config API).
"""

import pytest
from unittest.mock import patch, MagicMock

import agentgraph.easy as easy_module
from agentgraph.easy import (
    log,
    query,
    search,
    entity,
    link,
    track,
    connect,
    share,
)


@pytest.fixture(autouse=True)
def reset_easy_state():
    """Reset easy mode state before each test."""
    easy_module._initialized = False
    easy_module._api_key = None
    yield


class TestEasyLog:
    """Test the log() function."""
    
    def test_log_simple(self):
        """Test basic logging."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"id": "event-1"}
                
                easy_module._api_key = "test-key"
                log("did something")
                
                assert mock_post.called
    
    def test_log_with_type(self):
        """Test logging with event type."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"id": "event-1"}
                
                easy_module._api_key = "test-key"
                log("made a choice", type="decision")
                
                assert mock_post.called


class TestEasyQuery:
    """Test the query() function."""
    
    def test_query_simple(self):
        """Test basic query."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {
                    "answer": "you did stuff",
                    "events": []
                }
                
                easy_module._api_key = "test-key"
                result = query("what did I do?")
                
                assert result["answer"] == "you did stuff"


class TestEasyEntity:
    """Test the entity() function."""
    
    def test_create_entity(self):
        """Test entity creation."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"id": "entity-123"}
                
                easy_module._api_key = "test-key"
                result = entity("Acme Corp", type="user", industry="tech")
                
                assert result == "entity-123"


class TestEasyLink:
    """Test the link() function."""
    
    def test_create_link(self):
        """Test relationship creation."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"id": "rel-1"}
                
                easy_module._api_key = "test-key"
                link("entity-1", "entity-2", type="owns")
                
                assert mock_post.called


class TestTrackDecorator:
    """Test the @track decorator."""
    
    def test_track_function(self):
        """Test that @track logs function calls."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"id": "event-1"}
                
                easy_module._api_key = "test-key"
                
                @track
                def my_function(x):
                    return x * 2
                
                result = my_function(5)
                
                assert result == 10
                # Should have logged the call
                assert mock_post.called
    
    def test_track_preserves_errors(self):
        """Test that @track preserves exceptions."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"id": "event-1"}
                
                easy_module._api_key = "test-key"
                
                @track
                def failing_function():
                    raise ValueError("test error")
                
                with pytest.raises(ValueError):
                    failing_function()


class TestConnect:
    """Test the connect() function."""
    
    def test_connect_agent(self):
        """Test agent connection."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"status": "connected"}
                
                easy_module._api_key = "test-key"
                connect("MyAgent")
                
                assert mock_post.called


class TestShare:
    """Test the share() function."""
    
    def test_share_context(self):
        """Test sharing context."""
        with patch('agentgraph.easy._init'):
            with patch('agentgraph.easy.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"event_id": "share-1"}
                
                easy_module._api_key = "test-key"
                share("found something", topic="research", data={"key": "value"})
                
                assert mock_post.called


class TestServerAutoStart:
    """Test automatic server startup."""
    
    def test_easy_module_has_required_functions(self):
        """Test that easy module has the required functions."""
        assert callable(easy_module.log)
        assert callable(easy_module.query)
        assert callable(easy_module.entity)
        assert callable(easy_module.link)
        assert callable(easy_module.track)
    
    def test_init_sets_initialized(self):
        """Test that _init sets initialized flag."""
        with patch('agentgraph.easy._ensure_server'):
            with patch('agentgraph.easy._ensure_agent'):
                easy_module._initialized = False
                easy_module._init()
                assert easy_module._initialized
