#!/bin/bash
# Script to run the MCP rules engine server in the background

# Change to the project directory
cd "$(dirname "$0")"

# Activate the virtual environment
source venv-linux/bin/activate

# Set environment variables
export PYTHONPATH="$(pwd)"

# Kill any existing instances
pkill -f "rules_engine_mcp_sse.py" || true
pkill -f "updated_rules_engine_mcp.py" || true

# Create log directory if it doesn't exist
mkdir -p logs

# Start the server in the background
nohup python app/rules_engine_mcp_sse.py > logs/mcp_server.log 2>&1 &

# Save the PID
echo $! > mcp_server.pid

echo "MCP Rules Engine Server started with PID $(cat mcp_server.pid)"
echo "Logs available at: $(pwd)/logs/mcp_server.log"