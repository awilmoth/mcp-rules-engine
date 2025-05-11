# MCP Rules Engine

A flexible rules engine implementing the Model Context Protocol (MCP) to provide regex-based redaction for sensitive information. This engine can be used to redact personal identifiable information (PII) and other sensitive data before sending text to Large Language Models (LLMs).

## Features

- **Regex-Based Rules**: Define custom regex patterns to identify sensitive information
- **Multiple Rule Actions**: Support for redaction, transformation, flagging, and blocking
- **Rule Sets**: Group rules into sets for different contexts
- **Priority-Based Processing**: Apply rules in a specific order
- **MCP Integration**: Works with Claude and other LLMs that support the Model Context Protocol
- **HTTP and SSE Transport**: Flexible deployment options
- **Smithery Cloud Deployment**: Deploy to Smithery for managed hosting

## Quick Start

### Local Setup

1. **Create a virtual environment**:
   ```bash
   # Linux/WSL
   python -m venv venv-linux
   source venv-linux/bin/activate
   pip install -r requirements.txt
   
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run the MCP Server**:
   ```bash
   ./run_mcp_server.sh
   ```

3. **Test redaction functionality**:
   ```bash
   python test_redaction.py
   ```

### Using with Claude

Use the provided scripts to integrate with Claude CLI:

```bash
# Direct redaction and Claude integration
./use_direct_redaction.sh "My SSN is 123-45-6789 and my email is test@example.com"

# Smithery integration (after configuration)
./use_smithery.sh claude "My SSN is 123-45-6789 and my email is test@example.com"
```

## Redaction Patterns

The system includes default patterns for:

- Social Security Numbers (SSN)
- Credit Card Numbers
- Email Addresses
- Phone Numbers
- API Keys and Credentials
- IP Addresses
- URLs (flagging)

## Cloud Deployment

### Smithery Deployment

For a managed, cloud-hosted solution:

1. Run the preparation script:
   ```bash
   ./prepare_smithery_deployment.sh
   ```

2. Upload the generated files to Smithery
   - `smithery.json` - Configuration file
   - `rules_engine_mcp.zip` - Deployment package

3. Configure the Smithery integration:
   ```bash
   ./use_smithery.sh configure
   ```

See [SMITHERY_DEPLOYMENT.md](SMITHERY_DEPLOYMENT.md) for detailed instructions.

## Architecture

The Rules Engine consists of these main components:

1. **MCP Server**: Implements the Model Context Protocol
2. **Rules Engine**: Processes text according to defined rules
3. **Rule Management**: APIs for adding, updating, and managing rules
4. **Transport Layers**: HTTP API + SSE (Server-Sent Events) for streaming

## API Endpoints

- `/health` - Health check endpoint
- `/redact_text` - Redacts text directly
- `/process_text` - Processes text with options for rule sets
- `/mcp` - MCP JSON-RPC endpoint
- `/sse` - Server-Sent Events endpoint for MCP streaming
- `/mcp-tools` - Tool information endpoint

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.