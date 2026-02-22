from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Context

from safeclaw.mcp.tools import crawl_url, get_weather, summarize_content


# Helper to mock Context
def mock_context(headers: dict = None):
    ctx = MagicMock(spec=Context)
    ctx.headers = headers or {}
    ctx.request_id = "test-req-id"
    return ctx

@pytest.mark.asyncio
async def test_get_weather_allowed():
    with patch('safeclaw.mcp.tools.auth_client.check', new_callable=AsyncMock) as mock_check, \
         patch('safeclaw.actions.weather.execute', new_callable=AsyncMock) as mock_execute:

        mock_check.return_value = True
        mock_execute.return_value = "Weather in New York: Sunny"

        ctx = mock_context()
        result = await get_weather(location="New York", ctx=ctx)

        assert "Sunny" in result
        mock_check.assert_called_once()
        mock_execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_weather_denied():
    with patch('safeclaw.mcp.tools.auth_client.check', new_callable=AsyncMock) as mock_check:

        mock_check.return_value = False

        ctx = mock_context()

        with pytest.raises(ValueError, match="Permission denied"):
            await get_weather(location="New York", ctx=ctx)

@pytest.mark.asyncio
async def test_crawl_url_allowed():
    with patch('safeclaw.mcp.tools.auth_client.check', new_callable=AsyncMock) as mock_check, \
         patch('safeclaw.actions.crawl.CrawlAction.execute', new_callable=AsyncMock) as mock_execute:

        mock_check.return_value = True
        mock_execute.return_value = "Links found"

        ctx = mock_context()
        result = await crawl_url(url="https://example.com", ctx=ctx)

        assert result == "Links found"

@pytest.mark.asyncio
async def test_summarize_allowed():
    with patch('safeclaw.mcp.tools.auth_client.check', new_callable=AsyncMock) as mock_check, \
         patch('safeclaw.actions.summarize.SummarizeAction.execute', new_callable=AsyncMock) as mock_execute:

        mock_check.return_value = True
        mock_execute.return_value = "Summary"

        ctx = mock_context()
        result = await summarize_content(target="https://example.com", ctx=ctx)

        assert result == "Summary"

@pytest.mark.asyncio
async def test_admin_flush_cache_endpoint():
    from starlette.testclient import TestClient

    from safeclaw.mcp.server import mcp

    # We need to ensure startup hooks run? TestClient(lifespan="on") runs them.
    # But service.initialize() might fail if dependencies are missing (like SafeClaw).
    # We can mock service.initialize in lifespan?

    with patch('safeclaw.mcp.server.service.initialize', new_callable=AsyncMock), \
         patch('safeclaw.mcp.server.service.shutdown', new_callable=AsyncMock), \
         patch('safeclaw.mcp.server.auth_client.flush_cache', new_callable=AsyncMock) as mock_flush:

        app = mcp.http_app()
        # TestClient with app created from FastMCP
        with TestClient(app) as client:
            resp = client.post("/admin/flush-cache")
            assert resp.status_code == 200
            assert resp.json() == {"status": "Cache flushed"}
            mock_flush.assert_called_once()
