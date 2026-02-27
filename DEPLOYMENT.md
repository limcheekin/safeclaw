# SafeClaw MCP Server Deployment Guide

This guide provides comprehensive, step-by-step instructions for deploying the SafeClaw MCP (Model Context Protocol) Server into a production environment. It covers building the Docker image, configuring the environment variables, setting up the required infrastructure (Cerbos and Redis), and managing policies.

## 1. Prerequisites

Before deploying SafeClaw, ensure you have the following in your target environment:
- **Docker** and **Docker Compose** (or a container orchestration platform like Kubernetes)
- **Redis** server (for caching Cerbos authorization decisions)
- **Cerbos** PDP (Policy Decision Point) server

## 2. Infrastructure Setup: Redis and Cerbos

SafeClaw relies on Cerbos for authorization and Redis for caching those decisions to ensure low latency.

You can run Cerbos and Redis using Docker:

### Redis
```bash
docker run -d --name cerbos-redis -p 6379:6379 redis:7-alpine
```

### Cerbos PDP
Ensure your Cerbos policies (located in `./policies`) are accessible to the Cerbos container.
```bash
docker run -d --name cerbos-pdp \
  -p 3592:3592 -p 3593:3593 \
  -v $(pwd)/policies:/policies \
  ghcr.io/cerbos/cerbos:0.34.0 \
  server --set=storage.disk.directory=/policies \
         --set=server.httpListenAddr=:3592 \
         --set=server.grpcListenAddr=:3593
```

## 3. Building the SafeClaw Docker Image

SafeClaw includes a production-ready `Dockerfile`.

1. Navigate to the root of the SafeClaw repository.
2. Build the Docker image:
   ```bash
   docker build -t safeclaw-mcp:latest .
   ```

*Note: The `Dockerfile` assumes your project uses `pyproject.toml` and installs the required `mcp` optional dependencies. It runs the application using `uvicorn` on port 8000.*

## 4. Environment Variable Configuration

SafeClaw is configured entirely via environment variables. Create a `.env` file or export these variables in your deployment environment.

### Application Settings
- `APP_ENV`: Deployment environment (`development`, `staging`, `production`). Default: `development`.
- `LOG_LEVEL`: Logging verbosity (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`). Default: `INFO`.

### Cerbos Configuration
- `CERBOS_BASE_URL`: The URL where the Cerbos PDP is reachable. Example: `http://cerbos-pdp:3592`.
- `CERBOS_TIMEOUT_MS`: Timeout for Cerbos requests in milliseconds. Default: `500`.
- `CERBOS_CACHE_BACKEND`: Redis connection string for caching Cerbos decisions. Example: `redis://cerbos-redis:6379/0`.
- `CERBOS_CACHE_TTL_HIGH`: High TTL for cache in seconds. Default: `30`.
- `CERBOS_CACHE_TTL_MED`: Medium TTL for cache in seconds. Default: `60`.
- `CERBOS_CACHE_TTL_LOW`: Low TTL for cache in seconds. Default: `300`.
- `CERBOS_CIRCUIT_BREAKER_FAILURES`: Number of consecutive failures before opening the circuit breaker. Default: `5`.

### Principal Enrichment (Auth/JWT)
SafeClaw uses JSON Web Tokens (JWT) for authentication and principal extraction.

#### Generating a JWT Key Pair (RS256)
If you do not already have an authentication provider or a key pair, you can generate one for use between SafeClaw and your clients using OpenSSL:
```bash
# 1. Generate the private key
openssl genrsa -out private.pem 2048

# 2. Extract the public key
openssl rsa -in private.pem -pubout -out public.pem
```
You will use the **private key** (`private.pem`) to cryptographically sign tokens for your clients (like LocalAI), and provide the **public key** (`public.pem`) to SafeClaw so it can verify those tokens.

- `PRINCIPAL_ATTR_SOURCE`: Source of principal attributes (`jwt`, `introspect`, `user_service`). Default: `jwt`.
- `JWT_PUBLIC_KEY`: The public key to verify JWT signatures. You must provide the entire contents of your public key (e.g., `public.pem`), including the `-----BEGIN PUBLIC KEY-----` and `-----END PUBLIC KEY-----` markers. If providing this in a `.env` file or `docker-compose.yml`, make sure to correctly format or quote the multiline string.
- `USER_SERVICE_URL`: URL to fetch user details (if `user_service` is used).
- `AUTH_FALLBACK_MODE`: Behavior when auth context is missing (`deny` or `allow_with_logs`). Default: `deny`.

### Redis Configuration (General)
- `REDIS_URL`: Redis connection string for general application use. Example: `redis://cerbos-redis:6379/0`.

### MCP Server Settings
- `MCP_SERVER_NAME`: Name of your MCP server instance. Default: `safeclaw-mcp`.
- `MCP_SERVER_PORT`: Port to listen on. Default: `8000`.

## 5. Deploying the SafeClaw Server

Once your infrastructure is ready and your environment is configured, you can start the SafeClaw container.

### Using Docker Run
```bash
docker run -d --name safeclaw-app \
  -p 8000:8000 \
  -e APP_ENV=production \
  -e LOG_LEVEL=INFO \
  -e CERBOS_BASE_URL=http://<cerbos-host>:3592 \
  -e CERBOS_CACHE_BACKEND=redis://<redis-host>:6379/0 \
  -e REDIS_URL=redis://<redis-host>:6379/0 \
  -e MCP_SERVER_NAME=safeclaw-mcp \
  safeclaw-mcp:latest
```

### Using Docker Compose
For simpler deployments, you can use the provided `docker-compose.yml` to spin up the entire stack simultaneously:
```bash
docker-compose up -d --build
```
*Note: Ensure you review and update the environment variables within the `docker-compose.yml` file to match your production requirements before running this command.*

## 6. Managing Cerbos Policies

Authorization rules are defined in Cerbos policy files (e.g., `policies/resource_policies.yaml`).

### Deployment Considerations for Policies:
1. **Volume Mounting (Recommended for faster iteration):** Mount the `policies/` directory from the host machine into the Cerbos container as shown in step 2. This allows you to update policies without restarting containers.
2. **Baking into Image (Recommended for immutable infrastructure):** Create a custom `Dockerfile` that extends the base Cerbos image and copies your `policies/` directory into the image. This ensures policies are strictly versioned alongside your system deployments.

### Policy Validations
Before deploying new or updated policies to production, always validate and run tests against them using the Cerbos CLI:
```bash
cerbos compile ./policies
cerbos test ./policies
```

## 7. Health Checks and Observability

To ensure SafeClaw is operating correctly in production:
- **App Health**: `curl -f http://localhost:8000/sse` (or you can use the appropriate root endpoint exposed by the MCP server).
- **Cerbos Health**: `curl -f http://<cerbos-host>:3592/_cerbos/health`
- **Redis Health**: Use `redis-cli ping` to verify Redis connectivity.

### Metrics & Tracing
SafeClaw is designed to export Prometheus metrics and OpenTelemetry traces. Ensure you connect this telemetry data to your preferred observability platform (e.g., Grafana, Jaeger, Datadog) to monitor Cerbos authorization latency and application performance.
