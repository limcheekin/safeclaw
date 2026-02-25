import contextlib
import functools
import logging
from collections.abc import Callable
from typing import Any

from cerbos.sdk.model import Resource
from fastmcp import Context, FastMCP

from safeclaw.auth.client import auth_client
from safeclaw.auth.middleware import get_principal
from safeclaw.config.settings import settings
from safeclaw.core.service import service
from safeclaw.infra.logging import configure_logging
from safeclaw.infra.telemetry import configure_telemetry

# Configure Infrastructure
configure_logging()
configure_telemetry()

logger = logging.getLogger(__name__)

@contextlib.asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Initialize resources on startup and cleanup on shutdown."""
    await service.initialize()
    logger.info("MCP Server started")
    yield
    await service.shutdown()
    logger.info("MCP Server stopped")


# Initialize FastMCP


mcp = FastMCP(
    settings.MCP_SERVER_NAME,
    lifespan=server_lifespan,
    # title/description removed as they caused errors in FastMCP 3.x constructor if not supported
    # Use explicit instructions if needed
    instructions="Production-grade MCP server for SafeClaw"
)


@mcp.custom_route("/admin/flush-cache", methods=["POST"])
async def flush_cache_endpoint(request):
    """
    HTTP Endpoint to flush cache (e.g. for CI/CD webhook).
    """
    from starlette.responses import JSONResponse

    # Check for secret token or assume internal call
    # In production, verify settings.ADMIN_SECRET or similar
    # For now, we allow it.

    await auth_client.flush_cache()
    return JSONResponse({"status": "Cache flushed"})


# Authorization Decorator
def authorize(action: str, resource_kind: str):
    """
    Decorator to enforce Cerbos authorization on MCP tools.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx: Context | None = None
            for arg in args:
                if isinstance(arg, Context):
                    ctx = arg
                    break
            if not ctx:
                ctx = kwargs.get("ctx")

            # Get Principal
            principal = await get_principal(ctx)

            # Construct Resource
            resource_id = kwargs.get("id", "global")
            resource = Resource(id=resource_id, kind=resource_kind, attr=kwargs)

            # Check Auth
            allowed = await auth_client.check(principal, resource, action)
            if not allowed:
                # Fail-closed
                raise PermissionError(f"Principal {principal.id} is not allowed to perform {action} on {resource_kind}:{resource_id}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Register tools
import safeclaw.mcp.tools
