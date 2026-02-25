import asyncio
import os

import httpx
import pytest

BASE_URL = os.getenv("APP_URL", "http://localhost:8000")
CERBOS_URL = os.getenv("CERBOS_BASE_URL", "http://localhost:3592")

@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"), reason="Skipping integration tests")
@pytest.mark.asyncio
async def test_cerbos_health():
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            try:
                resp = await client.get(f"{CERBOS_URL}/_cerbos/health", timeout=2.0)
                if resp.status_code == 200:
                    return
            except (httpx.ConnectError, httpx.ReadError):
                pass
            await asyncio.sleep(2)
        pytest.fail("Cerbos is not reachable")

@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"), reason="Skipping integration tests")
@pytest.mark.asyncio
async def test_app_connectivity():
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            try:
                resp = await client.get(f"{BASE_URL}/", timeout=2.0)
                if resp.status_code in [200, 404, 405]:
                    return
            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
                pass
            await asyncio.sleep(2)
        pytest.fail("App is not reachable")
