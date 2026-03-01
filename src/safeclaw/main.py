from safeclaw.mcp.server import mcp

# Expose ASGI app for uvicorn.
# Uses stateless streamable-http transport at the standard /mcp endpoint.
#
# Why these options:
#   transport='streamable-http': LocalAI expects JSON-RPC responses in the
#     HTTP POST response body, not via a persistent SSE stream.
#   stateless_http=True: Each POST is self-contained (no session persistence
#     between requests). LocalAI does not send a Mcp-Session-Id header so
#     stateful sessions would not work anyway.
#   json_response=True: FastMCP's default requires the client to send
#     'Accept: text/event-stream', which LocalAI does not include. Setting
#     json_response=True switches to plain 'application/json' responses,
#     avoiding the 406 Not Acceptable error.
app = mcp.http_app(
    transport='streamable-http',
    stateless_http=True,
    json_response=True,
)

def main():
    """Run the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
