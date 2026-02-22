# SafeClaw MCP Server Runbook

## Incidents

### 1. PDP Unreachable
**Symptoms:**
- `cerbos_call_duration_seconds` high or timing out.
- `cerbos_decision_total{result="error"}` increasing.
- Audit logs showing `circuit_open`.

**Impact:**
- All restricted tools (weather, crawl, summarize) will fail (fail-closed).
- Read-only tools might work if cached.

**Mitigation:**
- Check Cerbos container status: `docker-compose ps cerbos`.
- Check logs: `docker-compose logs cerbos`.
- Verify connectivity: `curl http://localhost:3592/_cerbos/health`.
- If restarting doesn't help, rollback policy changes or scale up Cerbos if load is high.

### 2. High PDP Latency
**Symptoms:**
- P95 latency > 200ms.
- User experience degradation.

**Mitigation:**
- Check Redis cache hit rate: `cerbos_decision_cache_hit_total`.
- If cache hit rate is low, increase TTL in `config/settings.py` or check if keys are correct.
- Ensure Redis is running and healthy.

### 3. Policy Incorrectness (Access Denied for Valid Users)
**Symptoms:**
- Users complaining about "Permission denied".
- Audit logs show `decision: deny`.

**Mitigation:**
- Check `audit_logger` output for `reason`.
- Check `policies/resource_policies.yaml` for logic errors.
- Run policy tests: `cerbos compile policies/ --test=policies/testdata`.
- Rollback policy changes.

## Operations

### Flush Cache
To force a reload of decisions (e.g. after policy update without restart), run the `admin_flush_cache` tool via MCP.

```bash
# Example via mcp-cli or client
call_tool admin_flush_cache {}
```

### Policy Rollback
1. Revert changes in `policies/` directory.
2. Redeploy Cerbos container (mounts updated files).
3. Flush cache.
