from typing import Any

from cerbos.sdk.model import Resource
from fastmcp import Context

from safeclaw.actions import weather
from safeclaw.actions.crawl import CrawlAction
from safeclaw.actions.summarize import SummarizeAction
from safeclaw.auth.client import auth_client
from safeclaw.auth.middleware import get_principal
from safeclaw.core.service import service
from safeclaw.mcp.server import mcp

# Instantiate action handlers
crawl_action = CrawlAction()
summarize_action = SummarizeAction()

async def _check_auth(ctx: Context, action: str, resource_kind: str, resource_id: str, attrs: dict[str, Any] | None = None) -> None:
    """Helper to check authorization."""
    principal = await get_principal(ctx)
    attrs = attrs or {}
    resource = Resource(id=resource_id, kind=resource_kind, attr=attrs)

    allowed = await auth_client.check(principal, resource, action)
    if not allowed:
        # We can raise an error that FastMCP catches, or return a standardized error.
        # FastMCP might expose exceptions to the client.
        raise ValueError(f"Permission denied: {action} on {resource_kind}:{resource_id}")


@mcp.tool()
async def get_weather(location: str, ctx: Context, units: str = "imperial") -> str:
    """
    Get weather forecast for a location.

    Args:
        location: City name or coordinates.
        units: 'imperial' (F) or 'metric' (C).
    """
    await _check_auth(ctx, "read", "weather", location, {"location": location})

    engine = service.get_engine()
    params = {"location": location, "units": units}

    # Weather action is a module-level function
    return await weather.execute(params, "mcp_user", "mcp", engine)


@mcp.tool()
async def crawl_url(url: str, ctx: Context, depth: int = 0, same_domain: bool = True) -> str:
    """
    Crawl a website and extract links.

    Args:
        url: The URL to crawl.
        depth: Recursion depth (0 for single page).
        same_domain: Whether to restrict crawl to the same domain.
    """
    await _check_auth(ctx, "read", "crawl", url, {"url": url})

    engine = service.get_engine()
    params = {
        "url": url,
        "depth": depth,
        "same_domain": same_domain
    }

    # CrawlAction is a class
    return await crawl_action.execute(params, "mcp_user", "mcp", engine)


@mcp.tool()
async def summarize_content(target: str, ctx: Context, sentences: int = 5) -> str:
    """
    Summarize text or a webpage.

    Args:
        target: The text or URL to summarize.
        sentences: Number of sentences in the summary.
    """
    # Resource ID is hash of target or target itself if short
    resource_id = target[:64]
    await _check_auth(ctx, "read", "summarize", resource_id, {"target": target})

    engine = service.get_engine()
    params = {
        "target": target,
        "sentences": sentences
    }

    return await summarize_action.execute(params, "mcp_user", "mcp", engine)

# Add flush cache tool
@mcp.tool()
async def admin_flush_cache(ctx: Context) -> str:
    """
    Flush the Cerbos decision cache (Admin only).
    """
    await _check_auth(ctx, "flush", "system", "cache", {})

    await auth_client.flush_cache()
    return "Cache flushed successfully."
