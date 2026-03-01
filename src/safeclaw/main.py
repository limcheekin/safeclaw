from safeclaw.mcp.server import mcp
from starlette.middleware import Middleware

# Expose ASGI app for uvicorn.
# Use stateless streamable-http transport mounted at /sse:
#   - LocalAI POSTs to http://<host>/sse and expects the JSON-RPC response
#     directly in the HTTP response body (not via an SSE stream).
#   - stateless_http=True means each POST creates a fresh transport session,
#     so no GET /sse connection is needed and there is no session_id to track.
#   - The old RewriteSSEMiddleware (path rewriting + session_id injection +
#     body rewriting) is no longer required with this transport.
app = mcp.http_app(
    transport='streamable-http',
    path='/sse',
    stateless_http=True,
)

def main():
    """Run the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
