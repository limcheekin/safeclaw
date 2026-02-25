# SafeClaw MCP Developer Guide

This guide describes how to connect the Antigravity IDE to the SafeClaw MCP Server, run the automated integration tests against the tools, and manually validate the functionality of the implemented tools.

## Phase 1: Connecting Antigravity IDE to the MCP Server

The Antigravity IDE natively supports the latest Model Context Protocol (MCP) integrations using standard `sse` and `stdio` transports. Since SafeClaw's MCP server is exposed over HTTP/SSE via FastMCP, you connect it using the IDE's configuration file.

### Prerequisites

You must have the SafeClaw core services running in Docker Compose to expose the FastMCP Server on defined port 8000:
```bash
docker compose up -d app cerbos redis
```

### Steps

1. Navigate to the local `.gemini` state directory in your workspace:
2. Create or open the `.gemini/mcp.json` file.
3. Configure the `mcpServers` dict to map the name to your local SafeClaw SSE endpoint using the `sse` transport layer.

```json
{
    "mcpServers": {
        "safeclaw": {
            "url": "http://localhost:8000/sse",
            "transport": "sse"
        }
    }
}
```

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

> **Note on Permissions**: If you manually test through the IDE and Antigravity IDE connects as anonymous without providing a signed JWT Header, the server's Cerbos integration will intentionally yield a fail-closed PermissionError due to safety guardrails. Providing the right Header map in the `mcp.json` proxy allows it to spoof standard headers where JWT isn't native.
