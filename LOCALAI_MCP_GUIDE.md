# LocalAI MCP Configuration Guide for SafeClaw

This guide details how to configure LocalAI (running at `http://192.168.1.111:8880`) to use the SafeClaw MCP server (running at `http://192.168.1.111:9994/sse`) with JWT authentication.

## Prerequisites: JWT Authentication

The SafeClaw MCP server is configured to verify JWT tokens using the `JWT_PUBLIC_KEY` provided in your production deployment (`coolify-docker-compose.yml`). 

To authenticate LocalAI with the MCP server, you must provide a valid JWT.

1. Generate a JWT signed by the private key that corresponds to your production `JWT_PUBLIC_KEY`.
   - The token must be signed using the `RS256` algorithm.
   - The payload should ideally contain a `sub` (subject) claim representing the LocalAI agent (e.g., `{"sub": "localai"}`).
   - You can use the provided `generate_jwt_token.py` script to easily generate a compatible token. First, create a virtual environment and install the required Python libraries using `uv`:
     ```bash
     source .venv/bin/activate
     uv pip install PyJWT cryptography
     ```
   - Then, run the script pointing it to your private key:
     ```bash
     python generate_jwt_token.py --key private.pem --days 365
     ```
   - Make a note of the token printed in the output.
2. Keep this JWT handy; it will be used as the `<YOUR_GENERATED_JWT_TOKEN>` in the configurations below.

## Configuration Options

LocalAI's MCP integration is configured inside the model's YAML file. Since you are using the `ibm-granite-4.0-h-tiny` model, create or edit the YAML configuration file for this model in your LocalAI models directory (e.g., `models/ibm-granite-4.0-h-tiny.yaml`).

Here are two recommended setups depending on your needs:

### Option 1: Simple Tasks Configuration

This configuration is optimized for fast, straightforward tool usage without complex reasoning or auto-planning overhead.

```yaml
name: ibm-granite-4.0-h-tiny
# backend and parameters configurations depending on your model setup
mcp:
  remote: |
    {
      "mcpServers": {
        "safeclaw": {
          "url": "http://192.168.1.111:9994/sse",
          "token": "<YOUR_GENERATED_JWT_TOKEN>"
        }
      }
    }
agent:
  max_attempts: 2
  max_iterations: 2
  enable_reasoning: false
  enable_planning: false
```

### Option 2: Complex Tasks Configuration

This configuration enables advanced reasoning and planning, allowing the model to break down complex tasks and re-evaluate its approach.

```yaml
name: ibm-granite-4.0-h-tiny
# backend and parameters configurations depending on your model setup
mcp:
  remote: |
    {
      "mcpServers": {
        "safeclaw": {
          "url": "http://192.168.1.111:9994/sse",
          "token": "<YOUR_GENERATED_JWT_TOKEN>"
        }
      }
    }
agent:
  max_attempts: 5
  max_iterations: 5
  enable_reasoning: true
  enable_planning: true
  enable_mcp_prompts: true
```

*Note: Replace `<YOUR_GENERATED_JWT_TOKEN>` with the token generated in the prerequisites step.*

## Testing the Configuration

Once the model configuration is saved and LocalAI has reloaded it, you can test the MCP integration using the `/mcp/v1/chat/completions` endpoint. 

Run the following `curl` command to verify that LocalAI can successfully communicate with the SafeClaw MCP server:

```bash
curl http://192.168.1.111:8880/mcp/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ibm-granite-4.0-h-tiny",
    "messages": [
      {"role": "user", "content": "What tools are available to you?"}
    ],
    "temperature": 0.7
  }'
```

### Expected Result

If configured correctly, the model will access the SafeClaw MCP tools, process the request, and return a response detailing the tools it can use or performing a specific action based on the tools you prompt it to use.

## Troubleshooting

### Error: "Method Not Allowed" during initialization
If you see an error in the LocalAI console similar to:
`Failed to connect to MCP server error=calling "initialize": sending "initialize": Method Not Allowed url="http://192.168.1.111:9994/sse"`

This usually occurs if the SafeClaw server has not been updated with the LocalAI compatibility middleware. Ensure you have the latest SafeClaw code (which includes `RewriteSSEMiddleware`) and have restarted the MCP server. This middleware natively routes the `POST /sse` requests sent by LocalAI correctly.

### Error: Authentication/Invalid JWT
If you encounter an authentication error, verify that the JWT token is valid, hasn't expired, and was signed correctly to match the `JWT_PUBLIC_KEY` configured in your SafeClaw deployment.

### Error: "unsupported content type" during initialization
If you see an error in the LocalAI console similar to:
`Failed to connect to MCP server error=calling "initialize": sending "initialize": unsupported content type "" url="http://192.168.1.111:9994/sse"`

This error has two root causes that the `RewriteSSEMiddleware` resolves:

1. **Missing Content-Type header**: FastMCP's error-path responses (e.g., HTTP 400 for missing `session_id`) do not include a `Content-Type` header. LocalAI refuses to process responses without one. The middleware injects `Content-Type: application/json` into all responses that are missing it.

2. **Starlette 307 redirect**: The middleware rewrites `POST /sse` → `POST /messages/`. If only the `path` was updated (without `raw_path`), Starlette would issue a 307 redirect (no trailing slash → trailing slash), resulting in another empty `Content-Type` response. The middleware now updates both `scope["path"]` and `scope["raw_path"]` to the correct `/messages/` path.

Ensure you have the latest SafeClaw code and have restarted the MCP server.
