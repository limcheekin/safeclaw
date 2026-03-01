from safeclaw.mcp.server import mcp
from starlette.middleware import Middleware

class RewriteSSEMiddleware:
    """
    Middleware to fix LocalAI MCP compatibility.
    LocalAI sends POST requests for MCP message initialization to the exact same URL 
    it used for SSE (e.g., /sse). FastMCP by default expects POSTs at /messages.
    This rewrites the internal ASGI path to /messages so FastMCP processes it.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and scope.get("method") == "POST" and scope.get("path") == "/sse":
            scope["path"] = "/messages/"
            scope["raw_path"] = b"/messages/"
            
            # LocalAI drops the required session_id parameter dynamically sent in the SSE endpoint event. 
            # We intercept FastMCP's internal connection state to get the active session ID.
            starlette_app = scope.get("app")
            
            sse_transport = None
            if starlette_app and hasattr(starlette_app, "routes"):
                for route in starlette_app.routes:
                    if getattr(route, "path", "") in ("/messages", "/messages/"):
                        handler = getattr(route, "app", None)
                        # Check direct or wrapped via RequireAuthMiddleware
                        if hasattr(handler, "__self__"):
                            sse_transport = handler.__self__
                        elif hasattr(handler, "app") and hasattr(handler.app, "__self__"):
                            sse_transport = handler.app.__self__
                        break
            
            if sse_transport and hasattr(sse_transport, "_read_stream_writers"):
                writers = sse_transport._read_stream_writers
                if writers:
                    # Get the first active SSE session
                    session_id = str(list(writers.keys())[0])
                    qs = scope.get("query_string", b"").decode("utf-8")
                    if "sessionId" in qs and "session_id" not in qs:
                        # Translate sessionId -> session_id for FastMCP
                        qs = qs.replace("sessionId=", "session_id=")
                        scope["query_string"] = qs.encode("utf-8")
                    elif "session_id" not in qs:
                        # Inject first active ID if missing
                        new_qs = f"session_id={session_id}" if not qs else f"{qs}&session_id={session_id}"
                        scope["query_string"] = new_qs.encode("utf-8")
                        
        response_started = False
        async def wrapped_send(message: dict):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = message.setdefault("headers", [])
                has_ct = any(k.decode("latin1").lower() == "content-type" for k, v in headers)
                if not has_ct:
                    headers.append((b"content-type", b"application/json"))
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        except Exception as e:
            if "ClosedResourceError" in str(type(e)):
                # LocalAI sometimes drops the SSE GET stream right after sending the POST request,
                # causing anyio to throw ClosedResourceError when FastMCP tries to stream the response.
                if scope.get("type") == "http":
                    if not response_started:
                        from starlette.responses import Response
                        response = Response("Accepted despite closed stream", status_code=202)
                        await response(scope, receive, send)
                    else:
                        # Request is already streaming (e.g. GET /sse). Suppress the error cleanly.
                        pass
                else:
                    raise
            else:
                raise

# Expose ASGI app for uvicorn
app = mcp.http_app(transport='sse', middleware=[Middleware(RewriteSSEMiddleware)])

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
