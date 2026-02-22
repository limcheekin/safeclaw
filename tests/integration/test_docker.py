import os

import httpx
import pytest

BASE_URL = os.getenv("APP_URL", "http://localhost:8000")
CERBOS_URL = os.getenv("CERBOS_BASE_URL", "http://localhost:3592")

@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"), reason="Skipping integration tests")
@pytest.mark.asyncio
async def test_cerbos_health():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CERBOS_URL}/_cerbos/health")
            assert resp.status_code == 200
        except httpx.ConnectError:
            pytest.fail("Cerbos is not reachable")

@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"), reason="Skipping integration tests")
@pytest.mark.asyncio
async def test_app_connectivity():
    # Check if we can connect to the app port
    # Since FastMCP endpoints might be specific (e.g. /sse), we just check connectivity
    async with httpx.AsyncClient() as client:
        try:
            # Try to hit root, might get 404 but connection works
            resp = await client.get(f"{BASE_URL}/")
            assert resp.status_code in [200, 404, 405]
        except httpx.ConnectError:
            pytest.fail("App is not reachable")
