import hashlib
import json
import logging
import time

import pybreaker
import redis.asyncio as redis
from cerbos.sdk.grpc.client import AsyncCerbosClient
from cerbos.sdk.model import Principal, Resource

from safeclaw.auth.audit import audit_logger
from safeclaw.config.settings import settings
from safeclaw.infra.telemetry import (
    CERBOS_CALL_DURATION_SECONDS,
    CERBOS_DECISION_CACHE_HIT_TOTAL,
    CERBOS_DECISION_TOTAL,
    tracer,
)

logger = logging.getLogger(__name__)

# Circuit Breaker
breaker = pybreaker.CircuitBreaker(
    fail_max=settings.CERBOS_CIRCUIT_BREAKER_FAILURES,
    reset_timeout=30,
    name="cerbos_pdp",
)


class AuthClient:
    _instance = None
    client: AsyncCerbosClient
    redis: redis.Redis

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = AsyncCerbosClient(settings.CERBOS_BASE_URL)
            cls._instance.redis = redis.from_url(settings.REDIS_URL)  # Use generic REDIS_URL for now if cache backend is same
        return cls._instance

    def _get_cache_key(self, principal: Principal, resource: Resource, action: str) -> str:
        """
        Generate a cache key based on the request parameters.
        cerbos:decision:{sha256(principal|resource|action|attrs)}
        """
        # We construct a dictionary of the key components
        # Note: Principal and Resource objects need to be converted to dicts that include their ID, roles/kind, and attributes
        # We use a stable serialization.

        p_dict = {
            "id": principal.id,
            "roles": sorted(principal.roles),
            "attr": principal.attr,
            "policy_version": principal.policy_version,
            "scope": principal.scope
        }

        r_dict = {
            "kind": resource.kind,
            "id": resource.id,
            "attr": resource.attr,
            "policy_version": resource.policy_version,
            "scope": resource.scope
        }

        data = {
            "principal": p_dict,
            "resource": r_dict,
            "action": action,
        }

        # Serialize with sorted keys for determinism
        serialized = json.dumps(data, sort_keys=True, default=str)
        hashed = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"cerbos:decision:{hashed}"

    async def check(self, principal: Principal, resource: Resource, action: str) -> bool:
        """
        Check authorization with caching and circuit breaker.
        Fail-closed: Returns False on error.
        """
        cache_key = self._get_cache_key(principal, resource, action)
        request_id = "req_unknown" # In real app, pass request_id from context

        # 1. Check Cache
        try:
            cached_decision = await self.redis.get(cache_key)  # type: ignore
            if cached_decision is not None:
                CERBOS_DECISION_CACHE_HIT_TOTAL.labels(resource=resource.kind, action=action).inc()
                logger.debug(f"Cerbos cache hit for {cache_key}")
                decision = cached_decision.decode("utf-8") == "1"
                # Log audit event for cache hit (latency 0)
                audit_logger.log_decision(
                    request_id, principal, resource, action, decision, 0.0, reason="cache_hit"
                )
                return decision
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")

        # 2. Call PDP with Circuit Breaker
        decision = False
        start_time = time.time()
        try:
            async def _call_pdp():
                with tracer.start_as_current_span("cerbos_check"):
                    with CERBOS_CALL_DURATION_SECONDS.labels(action=action, resource=resource.kind).time():
                        return await self.client.is_allowed(action, principal, resource)  # type: ignore

            decision = await breaker.call_async(_call_pdp)
            latency = (time.time() - start_time) * 1000

            # Record metrics
            result_str = "allow" if decision else "deny"
            CERBOS_DECISION_TOTAL.labels(result=result_str, resource=resource.kind, action=action).inc()

            # Audit Log
            audit_logger.log_decision(
                request_id, principal, resource, action, decision, latency, reason="pdp_check"
            )

            # 3. Update Cache
            ttl = settings.CERBOS_CACHE_TTL_MED
            if "sensitivity" in resource.attr:
                if resource.attr["sensitivity"] == "high":
                    ttl = settings.CERBOS_CACHE_TTL_HIGH
                elif resource.attr["sensitivity"] == "low":
                    ttl = settings.CERBOS_CACHE_TTL_LOW

            try:
                await self.redis.setex(cache_key, ttl, "1" if decision else "0")  # type: ignore
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

            return decision

        except pybreaker.CircuitBreakerError:
            logger.error("Cerbos circuit breaker open. Fail-closed.")
            CERBOS_DECISION_TOTAL.labels(result="error", resource=resource.kind, action=action).inc()
            audit_logger.log_decision(
                request_id, principal, resource, action, False, 0.0, reason="circuit_open"
            )
            return False
        except Exception as e:
            logger.error(f"Cerbos PDP error: {e}", exc_info=True)
            CERBOS_DECISION_TOTAL.labels(result="error", resource=resource.kind, action=action).inc()
            audit_logger.log_decision(
                request_id, principal, resource, action, False, 0.0, reason=f"pdp_error: {e}"
            )
            return False

    async def flush_cache(self):
        """Flush the decision cache safely using SCAN."""
        try:
            pattern = "cerbos:decision:*"
            cursor = 0
            deleted_count = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)  # type: ignore
                if keys:
                    await self.redis.delete(*keys)  # type: ignore
                    deleted_count += len(keys)
                if cursor == 0:
                    break
            logger.info(f"Flushed {deleted_count} keys from Cerbos cache")
        except Exception as e:
            logger.error(f"Failed to flush cache: {e}")


auth_client = AuthClient()
