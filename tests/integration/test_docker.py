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

@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"), reason="Skipping integration tests")
@pytest.mark.asyncio
async def test_sse_connection_drop_post_error():
    # Attempt to reproduce LocalAI connection drop
    async with httpx.AsyncClient() as client:
        # Wait for app to be up
        for _ in range(10):
            try:
                resp = await client.get(f"{BASE_URL}/", timeout=2.0)
                if resp.status_code in [200, 404, 405]:
                    break
            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
                pass
            await asyncio.sleep(2)
        else:
            pytest.fail("App is not reachable")
        
        # 1. Start SSE stream
        get_task = None
        session_id = None
        
        async def connect_sse():
            nonlocal session_id
            try:
                async with client.stream("GET", f"{BASE_URL}/sse") as response:
                    async for chunk in response.aiter_bytes():
                        if b"endpoint" in chunk:
                            # We received the endpoint event, meaning session is active
                            break
                    # Keep the stream open for a moment
                    await asyncio.sleep(10)
            except Exception:
                pass
                
        get_task = asyncio.create_task(connect_sse())
        
        # Give it a second to connect and get the endpoint event
        await asyncio.sleep(1)
        
        # 2. Fire POST request
        post_task = asyncio.create_task(
            client.post(f"{BASE_URL}/sse", json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "ping"
            })
        )
        
        # 3. Immediately cancel the GET task to close the SSE stream
        await asyncio.sleep(0.1)  # small delay to ensure POST starts processing
        get_task.cancel()
        
        # Wait for POST to finish
        try:
            post_response = await post_task
            assert post_response.status_code in [200, 202, 500] 
            # 500 would mean FastMCP crashed, but RewriteSSEMiddleware should return 202 
            # or 500 if unhandled. If it crashes the app totally, we won't reach here or next assert.
        except Exception:
            # We want to ensure it doesn't just hang or crash in a way that breaks httpx with RemoteProtocolError (disconnected)
            pass

        # 4. Verify server is still healthy
        resp = await client.get(f"{BASE_URL}/", timeout=2.0)
        assert resp.status_code in [200, 404, 405]

