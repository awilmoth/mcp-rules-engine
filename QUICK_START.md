# MCP Rules Engine Quick Start Guide

This quick start guide will get you up and running with the MCP Rules Engine for redacting sensitive information when using Claude.

## Setup

1. **Start the MCP Server**

   ```bash
   ./run_mcp_server.sh
   ```

2. **Configure Claude CLI**

   ```bash
   claude mcp remove rules_engine -s local
   claude mcp add rules_engine http://localhost:6366 --transport sse --scope local
   ```

3. **Verify Setup**

   ```bash
   ./test_redaction.sh
   ```

## Usage

Now when you use Claude, sensitive information like emails, SSNs, credit cards, and API keys will be automatically redacted.

```bash
claude
```

## Test Redaction

You can directly test the redaction API:

```bash
curl -X POST http://localhost:6366/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "My email is test@example.com and SSN 123-45-6789"}'
```

## One-Step Startup

For convenience, you can use the included wrapper script:

```bash
./start-claude-with-mcp.sh
```

This script will start the MCP server if needed, configure Claude, and launch the Claude CLI.

## Supported Redactions

The MCP Rules Engine automatically redacts:
- Email addresses
- Social Security Numbers (SSNs)
- Credit card numbers
- Phone numbers
- API keys and credentials
- IP addresses
- URLs (flagging only)

For more detailed information, see `README_MCP_USAGE.md`.