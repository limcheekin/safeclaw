import json
import logging
import time
from typing import Any

from cerbos.sdk.model import Principal, Resource

logger = logging.getLogger("audit")

def sanitize(data: Any) -> Any:
    """
    Recursively sanitize sensitive fields in a dictionary or list.
    """
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if k.lower() in ["password", "token", "secret", "key"]:
                new_data[k] = "***"
            else:
                new_data[k] = sanitize(v)
        return new_data
    elif isinstance(data, list):
        return [sanitize(item) for item in data]
    else:
        return data


class AuditLogger:
    def log_decision(
        self,
        request_id: str,
        principal: Principal,
        resource: Resource,
        action: str,
        decision: bool,
        latency_ms: float,
        reason: str | None = None,
        policy_ids: list[str] | None = None,
    ) -> None:
        """
        Log an audit event for an authorization decision.
        """
        event = {
            "timestamp": time.time(),
            "request_id": request_id,
            "service": "safeclaw-mcp",
            "tool": "pdp",
            "principal": {
                "id": principal.id,
                "roles": principal.roles,
                "attr": sanitize(principal.attr),
            },
            "resource": {
                "kind": resource.kind,
                "id": resource.id,
                "attr": sanitize(resource.attr),
            },
            "action": action,
            "decision": "allow" if decision else "deny",
            "pdp_latency_ms": latency_ms,
            "reason": reason,
            "policy_ids": policy_ids or [],
        }

        # Log as INFO level to audit logger
        # The JSON formatter will handle the structure if configured correctly
        # But here we are constructing the structure manually.
        # We can just dump it as message or pass as extra.

        logger.info(json.dumps(event))

audit_logger = AuditLogger()
