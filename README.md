# SafeClaw MCP Server

Transform SafeClaw into a production-grade MCP (Model Context Protocol) server with Cerbos authorization.

## Architecture

- **Domain**: SafeClaw actions (`weather`, `crawl`, `summarize`) wrapped as MCP tools.
- **MCP**: FastMCP (v3) server implementation (`src/safeclaw/mcp/`).
- **Auth**: Cerbos (PDP) integration with Redis cache and circuit breaker (`src/safeclaw/auth/`).
- **Config**: Pydantic settings (`src/safeclaw/config/`).
- **Infra**: Docker Compose, Makefile, Logging, Telemetry.

## Authorization Model

- **Principal**:
  - `user`: Standard user role.
  - `admin`: Full access.
  - `owner`: Derived role for resource ownership.
- **Resources**:
  - `weather`: `read` allowed for `user`, `admin`.
  - `crawl`: `read` allowed for `admin`; `user` restricted to safe domains (e.g. github.com).
  - `summarize`: `read` allowed for `user`, `admin`.
  - `system`: `flush` cache allowed for `admin`.

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Running Locally

1. **Build and Start**:
   ```bash
   make build
   make up
   ```
   This starts:
   - SafeClaw MCP Server (http://localhost:8000)
   - Cerbos PDP (http://localhost:3592)
   - Redis (localhost:6379)

2. **Check Health**:
   - App: `curl http://localhost:8000` (or appropriate endpoint)
   - Cerbos: `curl http://localhost:3592/_cerbos/health`

3. **Run Tests**:
   ```bash
   make test
   make integration-test
   ```

### Development

- **Add Tool**: Add function in `src/safeclaw/mcp/tools.py` with `@mcp.tool`. Use `_check_auth` helper.
- **Add Policy**: Edit `policies/resource_policies.yaml`. Add test case in `policies/testdata/test_suite.yaml`.
- **Lint**: `make lint`

## Operational Guarantees

- **Fail-Closed**: If Cerbos is unreachable or errors, access is denied.
- **Resilience**: Redis caching for decisions (TTL configurable), Circuit Breaker for PDP calls.
- **Observability**: Prometheus metrics and OpenTelemetry tracing.

## Deployment

- Use `Dockerfile` to build the image.
- Configure via Environment Variables (see `src/safeclaw/config/settings.py`).
- Ensure Cerbos policy files are mounted or baked into the image.

## License
MIT
