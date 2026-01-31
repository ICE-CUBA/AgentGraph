"""
Run AgentGraph MCP Server as a module.

Usage:
    python -m agentgraph.mcp                          # Stdio transport
    python -m agentgraph.mcp --transport http         # HTTP transport on port 8081
    python -m agentgraph.mcp --api-key YOUR_KEY       # With authentication
"""

from .server import run_mcp_server

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AgentGraph MCP Server - Connect AI coding tools to AgentGraph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Start with stdio transport (for Claude Desktop, Cursor, etc.)
    python -m agentgraph.mcp
    
    # Start with HTTP transport
    python -m agentgraph.mcp --transport http --port 8081
    
    # With custom AgentGraph server and API key
    python -m agentgraph.mcp --agentgraph-url http://myserver:8080 --api-key abc123

Integration with Claude Code:
    claude mcp add agentgraph python -m agentgraph.mcp

Integration with Cursor:
    Add to cursor settings.json:
    {
        "mcpServers": {
            "agentgraph": {
                "command": "python",
                "args": ["-m", "agentgraph.mcp"]
            }
        }
    }
"""
    )
    parser.add_argument(
        "--transport", 
        choices=["stdio", "http"], 
        default="stdio",
        help="Transport type (default: stdio for CLI integration)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8081,
        help="Port for HTTP transport (default: 8081)"
    )
    parser.add_argument(
        "--agentgraph-url", 
        default="http://localhost:8080",
        help="AgentGraph API server URL (default: http://localhost:8080)"
    )
    parser.add_argument(
        "--api-key", 
        default=None,
        help="API key for AgentGraph authentication (or set AGENTGRAPH_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    run_mcp_server(
        transport=args.transport,
        port=args.port,
        agentgraph_url=args.agentgraph_url,
        api_key=args.api_key
    )
