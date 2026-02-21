import logging
import os
from typing import Any

import jwt
from cerbos.sdk.model import Principal
from fastmcp import Context

from safeclaw.config.settings import settings

logger = logging.getLogger(__name__)

async def get_principal(ctx: Context | None = None) -> Principal:
    """
    Constructs a Cerbos Principal based on the execution context.
    Supports JWT, trusted headers, or environment fallback.
    """

    # Default principal for local/stdio usage
    principal_id = "local_user"
    roles = ["user"]
    attr: dict[str, Any] = {
        "source": "local",
        "assurance_level": "low",
    }

    # If we are in an HTTP context (SSE), we might have headers in the context
    headers = {}
    if ctx and hasattr(ctx, "headers"):
        headers = ctx.headers or {}

    # 1. Trusted Headers (Reverse Proxy)
    if settings.PRINCIPAL_ATTR_SOURCE == "introspect":
        if "x-user-id" in headers:
            principal_id = headers["x-user-id"]
            attr["source"] = "header"
            attr["assurance_level"] = "medium"
        if "x-user-role" in headers:
            roles = headers["x-user-role"].split(",")

    # 2. JWT
    elif settings.PRINCIPAL_ATTR_SOURCE == "jwt":
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Verify JWT using provided public key if available
                # If key is missing but source is jwt, we might decode unverified (NOT SAFE for prod, but handled by assurance level?)
                # Requirement: "validate attribute provenance; do not trust unverified headers by default"

                if settings.JWT_PUBLIC_KEY:
                    # Convert to bytes if it's a string key or fetch JWKS (out of scope for quickstart but good to simulate)
                    # Assuming public key string PEM
                    payload = jwt.decode(
                        token,
                        settings.JWT_PUBLIC_KEY,
                        algorithms=["RS256", "ES256", "HS256"]
                    )
                    attr["assurance_level"] = "high"
                else:
                    # Development/fallback
                    if settings.APP_ENV == "production":
                        logger.error("JWT_PUBLIC_KEY not set in production. Rejecting unverified JWT.")
                        raise ValueError("Missing public key")

                    logger.warning("Decoding JWT without verification (dev only)")
                    payload = jwt.decode(token, options={"verify_signature": False})
                    attr["assurance_level"] = "low"

                principal_id = payload.get("sub", principal_id)
                roles = payload.get("roles", roles)
                if isinstance(roles, str):
                    roles = [roles]

                attr["source"] = "jwt"
                # Copy other claims
                for k, v in payload.items():
                    if k not in ["sub", "roles", "exp", "iat", "aud"]:
                        attr[k] = v

            except Exception as e:
                logger.warning(f"JWT decode failed: {e}")
                if settings.AUTH_FALLBACK_MODE == "deny":
                    # If we expected JWT but failed, we might want to return an anonymous principal or fail?
                    # Since this function returns a Principal, returning a fallback "anonymous" is safer than crashing
                    # unless strict.
                    principal_id = "anonymous"
                    roles = ["anonymous"]
                    attr["assurance_level"] = "none"

    # 3. User Service Enrichment (Placeholder)
    if settings.USER_SERVICE_URL:
        pass

    logger.debug(f"Resolved principal: {principal_id}, roles: {roles}")

    return Principal(
        id=principal_id,
        roles=roles,
        attr=attr,
    )
