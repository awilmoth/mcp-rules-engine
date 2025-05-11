#!/bin/bash
# Script to stop the MCP rules engine server

# Change to the project directory
cd "$(dirname "$0")"

# Check if PID file exists
if [ -f mcp_server.pid ]; then
    PID=$(cat mcp_server.pid)

    # Check if the process is still running
    if ps -p $PID > /dev/null; then
        echo "Stopping MCP Rules Engine Server (PID: $PID)..."
        kill $PID
        rm mcp_server.pid
        echo "Server stopped."
    else
        echo "Server not running (stale PID file)."
        rm mcp_server.pid
    fi
else
    # Try to find and kill any running instances
    PID=$(pgrep -f "rules_engine_mcp_sse.py")
    if [ -n "$PID" ]; then
        echo "Stopping MCP Rules Engine Server (PID: $PID)..."
        kill $PID
        echo "Server stopped."
    else
        # Also check for the original script
        PID=$(pgrep -f "updated_rules_engine_mcp.py")
        if [ -n "$PID" ]; then
            echo "Stopping legacy MCP Rules Engine Server (PID: $PID)..."
            kill $PID
            echo "Server stopped."
        else
            echo "No running MCP Rules Engine Server found."
        fi
    fi
fi