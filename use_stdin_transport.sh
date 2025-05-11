#!/bin/bash

# Script to use stdin transport for MCP

# Change to the project directory
cd "$(dirname "$0")"

# Make sure the MCP server is running
if ! curl -s http://localhost:6366/health > /dev/null; then
  echo "MCP server is not running. Starting it..."
  ./run_mcp_server.sh
  
  # Wait a moment for the server to start
  sleep 2
  
  # Verify it started
  if ! curl -s http://localhost:6366/health > /dev/null; then
    echo "Failed to start MCP server. Please check logs."
    exit 1
  fi
  echo "MCP server started successfully."
else
  echo "MCP server is already running."
fi

# Create a temporary MCP config file for this run
cat > temp_mcp_config.json << EOF
{
  "mcpServers": {
    "rules_engine": {
      "url": "http://localhost:6366/redact_text",
      "transport": "http",
      "timeout_ms": 30000,
      "protocol_version": "execute",
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
        }
      ]
    }
  }
}
EOF

echo "Testing direct redaction with: 'Test SSN: 123-45-6789'"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"text": "Test SSN: 123-45-6789"}' \
  http://localhost:6366/redact_text | jq

echo -e "\nRunning Claude with custom MCP config..."
echo "The MCP rules_engine should automatically redact sensitive information."
echo "Try entering 'My SSN is 123-45-6789 and my email is test@example.com'"

# Run Claude with the custom MCP config
claude --mcp-config temp_mcp_config.json "$@"

# Clean up temporary file when done
rm -f temp_mcp_config.json