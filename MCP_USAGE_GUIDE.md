# MCP Redaction Service Usage Guide

This guide explains how to use the MCP (Model Context Protocol) Redaction Service to protect sensitive information when using Claude and other LLMs.

## Overview

The MCP Redaction Service is a privacy-enhancing tool that automatically detects and redacts sensitive information such as:

- Social Security Numbers (SSNs)
- Credit card numbers
- Email addresses
- Phone numbers
- API keys and credentials
- IP addresses
- URLs (flagging only)

## Starting the Service

The MCP server runs as a standalone HTTP service on port 6366:

```bash
# Start the MCP server
cd /home/aaron/mcp-redacted
./run_mcp_server.sh

# Verify it's running
curl http://localhost:6366/health
```

## Usage Options

### 1. Using Claude CLI with MCP Redaction

You can use Claude CLI with the MCP redaction service using the `start-claude-with-mcp.sh` script:

```bash
./start-claude-with-mcp.sh
```

For non-interactive use (if you're experiencing terminal issues):

```bash
echo "My SSN is 123-45-6789" | claude -p
```

### 2. Direct API Client

For direct programmatic access to the redaction service, use the `direct_api_client.py`:

```bash
# Show available MCP tools
./direct_api_client.py --list-tools

# Redact text from command line
./direct_api_client.py --text "My SSN is 123-45-6789"

# Redact text from a file
./direct_api_client.py --file input.txt --output redacted.txt

# Get JSON output
./direct_api_client.py --text "My SSN is 123-45-6789" --json
```

This client supports:
- Command line text input
- File input/output
- Interactive text input mode
- JSON output format

### 3. Claude API Integration

For integrating with the Claude API, use the API integration example in `api_integration_example.py`:

```bash
# Redact before sending to Claude API
./api_integration_example.py --text "My SSN is 123-45-6789"

# Skip redaction (for comparison)
./api_integration_example.py --text "My SSN is 123-45-6789" --no-redact

# Use a specific Claude model
./api_integration_example.py --text "My SSN is 123-45-6789" --model claude-3-sonnet-20240229
```

## MCP Server Configuration

The MCP server is configured in `/home/aaron/mcp-redacted/claude-code-config.json` with these settings:

```json
{
  "mcpServers": {
    "rules_engine": {
      "url": "http://localhost:6366/sse",
      "transport": "sse",
      "timeout_ms": 120000,
      "protocol_version": "tools/call",
      "command": "/home/aaron/mcp-redacted/venv-linux/bin/python",
      "args": [
        "/home/aaron/mcp-redacted/app/rules_engine_mcp_sse.py"
      ],
      "env": {
        "PYTHONPATH": "/home/aaron/mcp-redacted"
      },
      "tools": [
        {
          "name": "redact_text",
          "description": "Redacts sensitive information from text based on configured patterns.",
          "parameters": {
            "text": {
              "type": "string",
              "description": "The text to redact"
            }
          }
        },
        {
          "name": "process_text",
          "description": "Processes text through rules engine with options for rule sets.",
          "parameters": {
            "text": {
              "type": "string",
              "description": "The text to process"
            },
            "rule_sets": {
              "type": "array",
              "description": "Optional IDs of rule sets to apply",
              "items": {
                "type": "string"
              }
            }
          }
        }
      ]
    }
  }
}
```

## Testing

You can verify the MCP server is running correctly with:

```bash
python test_claude_mcp.py
```

## Available Endpoints

The MCP server exposes these endpoints:

- `GET /health` - Check if the server is running
- `POST /redact_text` - Redact sensitive information from text
- `POST /process_text` - Process text with more options (rule sets, etc.)
- `GET /mcp-tools` - List available tools
- `POST /mcp` - JSON-RPC endpoint for MCP tools
- `GET /sse` - Server-Sent Events endpoint for MCP streaming

## Example API Responses

Example `redact_text` response:

```json
{
  "redacted_text": "My SSN is <SSN>",
  "matches": [
    {
      "original": "123-45-6789",
      "replacement": "<SSN>",
      "rule_name": "SSN"
    }
  ]
}
```

## Direct Testing via cURL

```bash
curl -X POST http://localhost:6366/redact_text \
  -H "Content-Type: application/json" \
  -d '{"text": "My email is test@example.com and SSN 123-45-6789"}'
```

## Customizing Redaction Rules

To modify existing rules or add new ones, you can edit the rules file directly:
```
app/RulesEngineMCP/rules_config.json
```

Alternatively, you can use the MCP API to programmatically manage rules.

## Troubleshooting

If the MCP server isn't working:

1. Check if it's running with `curl http://localhost:6366/health`
2. Look at logs in `/home/aaron/mcp-redacted/logs/mcp_server.log`
3. Restart the server with `./stop_mcp_server.sh && ./run_mcp_server.sh`
4. Ensure the transport is set to "sse" in configuration for better compatibility