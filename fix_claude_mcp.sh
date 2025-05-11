#!/bin/bash

# Script to fix the Claude MCP connection

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

# Remove any existing MCP configuration
echo "Removing existing MCP configuration..."
claude mcp remove rules_engine -s local 2>/dev/null || true

# Add the MCP server with SSE transport
echo "Adding MCP server with SSE transport..."
claude mcp add rules_engine "http://localhost:6366/sse" --transport sse --scope local

echo "MCP configuration fixed. Test it with:"
echo "  claude /mcp"
echo "  claude \"Test with SSN: 123-45-6789\""