import logging
import uvicorn
from fastmcp import FastMCP
from safeclaw.config.settings import settings
from safeclaw.mcp.server import mcp
import safeclaw.mcp.tools  # Register tools

# Expose ASGI app for uvicorn
app = mcp.http_app()

def main():
    """Run the MCP server."""
    # Run with uvicorn directly or via mcp.run()
    # mcp.run() supports stdio or sse.
    # But for production-grade, we often use uvicorn explicitly if we want health endpoints easily.
    # However, FastMCP 0.1.0 run() handles arguments.

    # We will use mcp.run() as it parses args.
    mcp.run()

if __name__ == "__main__":
    main()
