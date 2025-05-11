#!/bin/bash

# Script to use Claude with HTTP transport MCP for redaction

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

if [ $# -eq 0 ]; then
  echo "Usage: $0 \"Your text with sensitive information\""
  echo "Example: $0 \"My SSN is 123-45-6789 and my email is test@example.com\""
  exit 1
fi

echo "Original text: $1"
echo -e "\nRedacted version using direct API call:"
REDACTED=$(curl -s -X POST -H "Content-Type: application/json" \
  -d "{\"text\": \"$1\"}" \
  http://localhost:6366/redact_text | jq -r '.redacted_text')
echo "$REDACTED"

echo -e "\nSending to Claude with redaction:"
claude --mcp-config temp_mcp_config.json --print "$1"

# Clean up temporary file
rm -f temp_mcp_config.json