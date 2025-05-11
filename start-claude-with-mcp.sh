#!/bin/bash

# Set the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if rules engine is already running
if ! curl -s http://localhost:6366/health &>/dev/null; then
  echo "Starting MCP Rules Engine server..."
  # Start the rules engine server in the background
  source "$PROJECT_DIR/venv-linux/bin/activate" && \
  nohup python "$PROJECT_DIR/app/rules_engine_mcp_sse.py" > "$PROJECT_DIR/logs/rules_engine.log" 2>&1 &

  # Wait a moment for the server to start
  sleep 2

  # Check if it started successfully
  if curl -s http://localhost:6366/health &>/dev/null; then
    echo "MCP Rules Engine server started successfully."
  else
    echo "Warning: MCP Rules Engine server didn't start properly."
  fi
else
  echo "MCP Rules Engine server is already running."
fi

# Remove any existing MCP configuration for rules_engine and add a new one
claude mcp remove rules_engine -s local 2>/dev/null || true

echo "Adding MCP server configuration..."
# Configure MCP using SSE transport mode
claude mcp add rules_engine "http://localhost:6366/sse" \
  --transport sse --scope local || {
  echo "Warning: Could not configure MCP server. Functionality may be limited."
}

echo "Starting Claude with MCP redaction enabled..."
echo "- MCP server is active at http://localhost:6366"
echo "- Configured tools: redact_text, process_text"
echo "- Redaction applies to: emails, SSNs, credit cards, API keys, IPs, etc."

# Run Claude CLI with the requested arguments
claude "$@"