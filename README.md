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

We provide multiple integration options for Claude:

#### 1. Direct Redaction Pipeline

Use the direct redaction script for the simplest integration:

```bash
./use_direct_redaction.sh "My SSN is 123-45-6789 and my email is test@example.com"
```

This will:
1. Redact sensitive information
2. Send the redacted text to Claude
3. Display Claude's response

#### 2. Smithery Integration

For cloud-based integration with Smithery:

```bash
# Set up Smithery
./smithery_setup.sh install YOUR_SMITHERY_API_KEY

# Test redaction
./smithery_setup.sh test "My SSN is 123-45-6789"
```

See [SMITHERY_SETUP.md](SMITHERY_SETUP.md) for detailed instructions.

## Available Scripts

| Script | Description |
|--------|-------------|
| `run_mcp_server.sh` | Start the MCP server |
| `stop_mcp_server.sh` | Stop the running MCP server |
| `test_redaction.py` | Test the redaction functionality |
| `use_direct_redaction.sh` | Redact text and send to Claude |
| `smithery_setup.sh` | Manage Smithery integration |

## Redaction Patterns

The system includes default patterns for:

- Social Security Numbers (SSN): `\b\d{3}-\d{2}-\d{4}\b`
- Credit Card Numbers: `\b(?:\d{4}[- ]?){3}\d{4}\b`
- Email Addresses: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
- Phone Numbers: `\b(?:\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b`
- API Keys and Credentials: `(?i)(password|api[_-]?key|access[_-]?token|secret)[=:]\s*\S+`
- IP Addresses: `\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b`

## Cloud Deployment

### Smithery Deployment

For a managed, cloud-hosted solution:

1. Run the Smithery setup script:
   ```bash
   ./smithery_setup.sh install YOUR_SMITHERY_API_KEY
   ```

2. List installed servers:
   ```bash
   ./smithery_setup.sh list
   ```

3. Test redaction through Smithery:
   ```bash
   ./smithery_setup.sh test "My SSN is 123-45-6789"
   ```

See [SMITHERY_SETUP.md](SMITHERY_SETUP.md) for detailed instructions.

## API Endpoints

The MCP server exposes these endpoints:

- `/health` - Health check endpoint
- `/redact_text` - Redacts text directly
- `/process_text` - Processes text with options for rule sets
- `/mcp` - MCP JSON-RPC endpoint
- `/sse` - Server-Sent Events endpoint for MCP streaming
- `/mcp-tools` - Tool information endpoint

## Example: Direct API Redaction

```python
import requests

def redact_text(text):
    response = requests.post(
        "http://localhost:6366/redact_text", 
        json={"text": text}
    )
    return response.json()["redacted_text"]

sensitive_text = "My SSN is 123-45-6789 and email is test@example.com"
redacted_text = redact_text(sensitive_text)
print(redacted_text)  # "My SSN is <SSN> and email is <EMAIL>"
```

## Adding Custom Rules

You can add custom rules through the API or by modifying the rules configuration file:

```python
import requests

new_rule = {
    "name": "Custom Pattern",
    "description": "My custom redaction pattern",
    "condition": r"\bCUSTOM-\d{5}\b",  # Regex pattern
    "action": "redact",
    "replacement": "<CUSTOM>",
    "priority": 50
}

response = requests.post(
    "http://localhost:6366/add_rule", 
    json=new_rule
)
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.