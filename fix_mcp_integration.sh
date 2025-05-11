#!/bin/bash

# Script to fix MCP integration with Claude CLI using stdio transport

# Change to the project directory
cd "$(dirname "$0")"

# Stop any running MCP instances
./stop_mcp_server.sh

echo "Creating MCP configuration for stdio transport..."

# Remove any existing MCP configuration
echo "Removing existing MCP configuration..."
claude mcp remove rules_engine -s local 2>/dev/null || true

# Register the MCP server with stdio transport
echo "Registering new MCP server with stdio transport..."
claude mcp add rules_engine "/home/aaron/mcp-redacted/venv-linux/bin/python" \
  "/home/aaron/mcp-redacted/app/rules_engine_mcp_sse.py" --transport stdio \
  --env PYTHONPATH=/home/aaron/mcp-redacted \
  --scope local

# Check the MCP configuration
echo -e "\nMCP Configuration:"
claude mcp list

# Test the MCP configuration
echo -e "\nTesting MCP configuration with Claude CLI..."
echo "Try the following command now:"
echo "   claude /mcp"
echo "   claude \"My SSN is 123-45-6789\""