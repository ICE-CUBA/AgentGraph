"""
Tests for CLI commands.
"""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from agentgraph.cli import AgentGraphCLI, main


@pytest.fixture
def cli():
    """Create CLI instance with mock server."""
    return AgentGraphCLI(base_url="http://test:8080", api_key="test-key")


class TestCLIInit:
    """Test CLI initialization."""
    
    def test_default_url(self):
        """Test default URL."""
        cli = AgentGraphCLI()
        assert "localhost:8080" in cli.base_url
    
    def test_custom_url(self):
        """Test custom URL."""
        cli = AgentGraphCLI(base_url="http://custom:9000")
        assert cli.base_url == "http://custom:9000"
    
    def test_env_url(self, monkeypatch):
        """Test URL from environment."""
        monkeypatch.setenv("AGENTGRAPH_URL", "http://env:8080")
        cli = AgentGraphCLI()
        assert cli.base_url == "http://env:8080"


class TestCLIQuery:
    """Test query command."""
    
    def test_query_text_output(self, cli, capsys):
        """Test query with text output."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = {
                "answer": "You worked on testing.",
                "events": [{"id": "1", "description": "test"}]
            }
            
            cli.query("what did I do?")
            
            captured = capsys.readouterr()
            assert "You worked on testing" in captured.out
    
    def test_query_json_output(self, cli, capsys):
        """Test query with JSON output."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = {"answer": "test", "events": []}
            
            cli.query("what did I do?", json_output=True)
            
            captured = capsys.readouterr()
            assert '"answer"' in captured.out


class TestCLIEvents:
    """Test events command."""
    
    def test_list_events(self, cli, capsys):
        """Test listing events."""
        with patch.object(cli, '_request') as mock_req:
            # CLI expects {"events": [...]} format
            mock_req.return_value = {
                "events": [
                    {
                        "id": "event-1",
                        "type": "tool.call",
                        "action": "search",
                        "description": "Searched for papers",
                        "timestamp": "2024-01-30T12:00:00",
                        "status": "success"
                    }
                ]
            }
            
            cli.events(limit=10)
            
            captured = capsys.readouterr()
            assert "search" in captured.out or "Searched" in captured.out


class TestCLIEntities:
    """Test entities command."""
    
    def test_list_entities(self, cli, capsys):
        """Test listing entities."""
        with patch.object(cli, '_request') as mock_req:
            # CLI expects {"entities": [...]} format
            mock_req.return_value = {
                "entities": [
                    {
                        "id": "entity-1",
                        "type": "user",
                        "name": "Acme Corp"
                    }
                ]
            }
            
            cli.entities()
            
            captured = capsys.readouterr()
            assert "Acme Corp" in captured.out or "user" in captured.out


class TestCLISearch:
    """Test search command."""
    
    def test_keyword_search(self, cli, capsys):
        """Test keyword search."""
        with patch.object(cli, '_request') as mock_req:
            # CLI expects {"results": [...]} format
            mock_req.return_value = {
                "results": [
                    {"id": "1", "description": "Found matching event"}
                ]
            }
            
            cli.search("test query")
            
            mock_req.assert_called()
    
    def test_semantic_search(self, cli, capsys):
        """Test semantic search."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = {
                "results": [
                    {"document": {"description": "test"}, "score": 0.9}
                ]
            }
            
            cli.search("test query", semantic=True)
            
            # Should call semantic endpoint
            call_args = str(mock_req.call_args)
            assert "semantic" in call_args


class TestCLILog:
    """Test log command."""
    
    def test_log_event(self, cli, capsys):
        """Test logging an event."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = {"id": "new-event"}
            
            cli.log(
                event_type="tool.call",
                action="search",
                description="Test search",
                input_data=None,
                tags=None,
                status="success"
            )
            
            mock_req.assert_called_once()
            captured = capsys.readouterr()
            assert "Logged" in captured.out or "event" in captured.out.lower()


class TestCLIGraph:
    """Test graph command."""
    
    def test_show_graph(self, cli, capsys):
        """Test showing graph."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = {
                "nodes": [{"id": "1", "name": "Test", "type": "user"}],
                "links": []
            }
            
            cli.graph()
            
            captured = capsys.readouterr()
            assert "Graph" in captured.out or "node" in captured.out.lower()


class TestCLIRegistry:
    """Test registry commands."""
    
    def test_registry_list(self, cli, capsys):
        """Test listing registered agents."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = [
                {
                    "id": "agent-1",
                    "name": "TestBot",
                    "status": "online",
                    "capabilities": [{"name": "search"}],
                    "description": "A test bot"
                }
            ]
            
            cli.registry_list()
            
            captured = capsys.readouterr()
            assert "TestBot" in captured.out
    
    def test_registry_register(self, cli, capsys):
        """Test registering an agent."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = {
                "id": "new-agent",
                "name": "NewBot"
            }
            
            cli.registry_register(
                name="NewBot",
                capabilities=["search", "translate"],
                description="A new bot"
            )
            
            captured = capsys.readouterr()
            assert "registered" in captured.out.lower() or "NewBot" in captured.out
    
    def test_registry_discover(self, cli, capsys):
        """Test discovering agents."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = [
                {
                    "id": "agent-1",
                    "name": "TranslatorBot",
                    "status": "online",
                    "endpoint": "http://translator:8000"
                }
            ]
            
            cli.registry_discover(capability="translate")
            
            captured = capsys.readouterr()
            assert "TranslatorBot" in captured.out or "Found" in captured.out
    
    def test_registry_stats(self, cli, capsys):
        """Test registry stats."""
        with patch.object(cli, '_request') as mock_req:
            mock_req.return_value = {
                "total_agents": 5,
                "online_agents": 3,
                "offline_agents": 2
            }
            
            cli.registry_stats()
            
            captured = capsys.readouterr()
            assert "5" in captured.out or "Stats" in captured.out


class TestCLIStatus:
    """Test status command."""
    
    def test_status_healthy(self, cli, capsys):
        """Test status when server is healthy."""
        with patch.object(cli, '_request') as mock_req:
            # Mock health check
            mock_req.side_effect = [
                {"status": "ok"},  # health
                {"agents": []},  # agents list
                {"total_agents": 0, "online_agents": 0}  # registry stats
            ]
            
            cli.status()
            
            captured = capsys.readouterr()
            assert "healthy" in captured.out.lower() or "✅" in captured.out


class TestCLIMain:
    """Test main entry point."""
    
    def test_no_command_shows_help(self, capsys):
        """Test that no command shows help."""
        with pytest.raises(SystemExit):
            with patch('sys.argv', ['agentgraph']):
                main()
    
    def test_status_command(self):
        """Test status command invocation."""
        with patch('agentgraph.cli.AgentGraphCLI') as mock_cli_class:
            mock_cli = MagicMock()
            mock_cli_class.return_value = mock_cli
            
            with patch('sys.argv', ['agentgraph', 'status']):
                main()
            
            mock_cli.status.assert_called_once()
