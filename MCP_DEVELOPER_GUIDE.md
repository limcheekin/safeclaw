# SafeClaw MCP Developer Guide

This guide describes how to connect the Antigravity IDE to the SafeClaw MCP Server, run the automated integration tests against the tools, and manually validate the functionality of the implemented tools.

## Phase 1: Connecting Antigravity IDE to the MCP Server

The Antigravity IDE requires Model Context Protocol (MCP) servers to communicate over standard input/output (STDIO). Since SafeClaw's MCP server is exposed over HTTP/SSE via FastMCP, you must use a bridge tool to connect them via the global configuration file.

### Prerequisites

You must have the SafeClaw core services running in Docker Compose to expose the FastMCP Server on defined port 8000:
```bash
docker compose up -d
```

### Steps

1. Locate your global Antigravity configuration file:
   - **Linux/macOS**: `~/.gemini/antigravity/mcp_config.json`
   - **Windows**: `%USERPROFILE%\.gemini\antigravity\mcp_config.json`
2. Create or open the `mcp_config.json` file.
3. Configure the `mcpServers` dict. Use the `mcp-remote` utility as a bridge to translate the IDE's STDIO messages to the server's SSE transport.

```json
{
    "mcpServers": {
        "safeclaw": {
            "command": "npx",
            "args": [
                "-y",
                "mcp-remote",
                "http://localhost:8000/sse"
            ],
            "env": {
                "x-user-id": "dev_admin",
                "x-user-role": "admin,user"
            }
        }
    }
}
```

By providing `env` variables matching the Cerbos header introspection keys (`x-user-id` and `x-user-role`), FastMCP's SSE HTTP connections will forward these properties enabling the server connection to spoof a recognized developer identity safely without managing full JWT tokens during local IDE testing.

4. Antigravity IDE constantly monitors this file and will hot-reload its MCP connections. The SafeClaw tools will dynamically load into the Assistant's native toolbox (visible as internal tools).

## Phase 2: Automated Validation

We maintain a custom Python integration script capable of connecting directly to the `/sse` FastMCP endpoint. It discovers registered tools and triggers them sequentially to validate routing and structural integrity.

### Authentication Checks
SafeClaw embeds Cerbos for request authorization. By default, HTTP contexts rely on JWTs or fallback roles. To run the automated script successfully without encountering "Permission denied" errors, the validation script forcefully constructs an unverified JWT payload assigning administrative roles.

### Script Execution

To validate the tools programmatically, use the `validate_mcp.py` script included in the codebase.

```bash
uv run python validate_mcp.py
```

### Expected Output

A healthy server will reply with the discovery of the tools, followed immediately by simulated executions of `get_weather`, `crawl_url`, `summarize_content`, and `admin_flush_cache` routed down to Cerbos for rule-checking.

## Phase 3: Manual Validation

Once the server is connected to the Antigravity IDE (via Phase 1), you have access to natively converse with the AI and command it to use SafeClaw.

To systematically validate the integration manually, initiate a chat session in the IDE requesting it to trigger the tools. For example:

### 1. Validate `get_weather`
**Prompt:** "What's the weather like in London according to the SafeClaw server?"
**Verification:** Wait for the AI action log to surface a `get_weather` call. Inspect the raw SSE output to verify the action invoked the SafeClaw Engine routing.

### 2. Validate `crawl_url`
**Prompt:** "Use the SafeClaw MCP to crawl https://example.com at depth 0."
**Verification:** Antigravity should use the `crawl_url` MCP tool targeting the domain.

### 3. Validate `summarize_content`
**Prompt:** "Please summarize 'This is a test document' using the SafeClaw summarizer."
**Verification:** The `summarize_content` function should activate, triggering `SummarizeAction.execute(target, sentences=5)`.

### 4. Validate `admin_flush_cache`
**Prompt:** "Flush the Cerbos decision cache on the SafeClaw system."
**Verification:** The `admin_flush_cache` command will execute successfully, clearing any stale role decisions enforced temporarily by Redis cache.

> **Note on Permissions**: The Cerbos integration enforces strict authorization on every tool execute call. To manually test through the IDE, Antigravity requires the environment variables (`x-user-id` and `x-user-role`) provided in Phase 1's `mcp_config.json`. Without these variables, the server will intentionally yield a fail-closed PermissionError denying execution.
