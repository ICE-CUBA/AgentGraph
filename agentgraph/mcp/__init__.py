"""
AgentGraph MCP Server

Model Context Protocol server for integrating AgentGraph with AI coding tools
like Claude Code, Cursor, Cline, Windsurf, and other MCP-compatible clients.
"""

from .server import create_mcp_server, run_mcp_server

__all__ = ["create_mcp_server", "run_mcp_server"]
