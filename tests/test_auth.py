from unittest.mock import AsyncMock, patch

import pytest
from cerbos.sdk.model import Principal, Resource

from safeclaw.auth.client import auth_client


@pytest.mark.asyncio
async def test_auth_client_allow():
    # Mock PDP and Redis
    with patch.object(auth_client, 'client', new_callable=AsyncMock) as mock_pdp, \
         patch.object(auth_client, 'redis', new_callable=AsyncMock) as mock_redis:

        mock_redis.get.return_value = None
        mock_pdp.is_allowed.return_value = True

        p = Principal("user1", roles=["user"])
        r = Resource(id="ny", kind="weather")

        result = await auth_client.check(p, r, "read")

        assert result is True
        # Verify cache set
        mock_redis.setex.assert_called_once()
        # Verify PDP call
        mock_pdp.is_allowed.assert_called_once()

@pytest.mark.asyncio
async def test_auth_client_deny():
    with patch.object(auth_client, 'client', new_callable=AsyncMock) as mock_pdp, \
         patch.object(auth_client, 'redis', new_callable=AsyncMock) as mock_redis:

        mock_redis.get.return_value = None
        mock_pdp.is_allowed.return_value = False

        p = Principal("user1", roles=["user"])
        r = Resource(id="ny", kind="weather")

        result = await auth_client.check(p, r, "read")

        assert result is False
        # Verify cache set with "0"
        args, _ = mock_redis.setex.call_args
        assert args[2] == "0"

@pytest.mark.asyncio
async def test_auth_client_cache_hit_allow():
    with patch.object(auth_client, 'client', new_callable=AsyncMock) as mock_pdp, \
         patch.object(auth_client, 'redis', new_callable=AsyncMock) as mock_redis:

        mock_redis.get.return_value = b"1"

        p = Principal("user1", roles=["user"])
        r = Resource(id="ny", kind="weather")

        result = await auth_client.check(p, r, "read")

        assert result is True
        mock_pdp.is_allowed.assert_not_called()

@pytest.mark.asyncio
async def test_auth_client_fail_closed():
    """Test that if PDP fails and no cache, we fail closed (False)."""
    with patch.object(auth_client, 'client', new_callable=AsyncMock) as mock_pdp, \
         patch.object(auth_client, 'redis', new_callable=AsyncMock) as mock_redis:

        mock_redis.get.return_value = None
        mock_pdp.is_allowed.side_effect = Exception("PDP Down")

        p = Principal("user1", roles=["user"])
        r = Resource(id="ny", kind="weather")

        result = await auth_client.check(p, r, "read")

        assert result is False
