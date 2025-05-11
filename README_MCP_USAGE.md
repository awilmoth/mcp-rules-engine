# MCP Rules Engine Usage Guide

This document explains how to use the MCP Rules Engine with Claude for redacting sensitive information.

## Overview

The MCP (Model Context Protocol) Rules Engine provides text redaction capabilities to protect sensitive information when sending text to Claude or other LLMs. It automatically detects and redacts:

- Email addresses
- Social Security Numbers (SSN)
- Credit card numbers
- Phone numbers
- API keys/credentials
- IP addresses
- URLs (flagging only)

## Getting Started

### 1. Start the MCP Server

First, start the MCP Rules Engine server:

```bash
./run_mcp_server.sh
```

This will start the server on port 6366. Verify it's running:

```bash
curl http://localhost:6366/health
```

Should return: `{"status":"ok","version":"1.0.0"}`

### 2. Configure Claude CLI

Configure the Claude CLI to use the MCP server with SSE transport:

```bash
# Remove any existing MCP configuration for rules_engine
claude mcp remove rules_engine -s local

# Add MCP server with SSE transport
claude mcp add rules_engine http://localhost:6366 --transport sse --scope local
```

Verify the configuration:

```bash
claude mcp get rules_engine
```

Should show:
```
rules_engine:
  Scope: Local (private to you in this project)
  Type: sse
  URL: http://localhost:6366
```

### 3. Use Claude with Redaction

Now when you use Claude, sensitive information will be automatically redacted.

### Starting Claude with MCP (Alternative)

You can also use the included wrapper script to start Claude with MCP integration:

```bash
./start-claude-with-mcp.sh
```

This script will:
1. Start the MCP Rules Engine server if it's not already running
2. Configure the Claude CLI with MCP settings
3. Launch Claude CLI with the proper MCP configuration

You can pass any Claude CLI arguments to the script:

```bash
./start-claude-with-mcp.sh --file document.txt
```

### Stopping the MCP Server

To stop the MCP Rules Engine server when you're done:

```bash
./stop-mcp-server.sh
```

## Testing MCP Functionality

You can test if the MCP Rules Engine is working correctly:

```bash
python test_mcp_integration.py
```

This will verify:
- Health endpoints
- Direct redaction via HTTP
- MCP protocol integration (both legacy and new protocol formats)

For testing Claude integration specifically:

```bash
python test_claude_mcp.py
```

## Troubleshooting

If you see "rules_engine: failed" when running `mcp` command:

1. Verify the server is running:
   ```bash
   curl http://localhost:6366/health
   ```

2. Check server logs:
   ```bash
   cat logs/mcp_server.log
   ```

3. Restart the server:
   ```bash
   ./run_mcp_server.sh
   ```

4. Reconfigure Claude CLI:
   ```bash
   claude mcp remove rules_engine -s local
   claude mcp add rules_engine http://localhost:6366 --transport sse --scope local
   ```

## Configuration

The MCP configuration is defined in `mcp-config.json`, which specifies:
- The server URL (http://localhost:6366)
- Protocol version (tools/call)
- Available tools (redact_text, process_text)

## Customizing Redaction Rules

To modify existing rules or add new ones, you can edit the rules file directly:
```
app/RulesEngineMCP/rules_config.json
```

Alternatively, you can use the MCP API to programmatically manage rules.

## Direct Testing

To test redaction directly via the API:

```bash
curl -X POST http://localhost:6366/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "My email is test@example.com and SSN 123-45-6789"}'
```