#!/bin/bash
# Start the Rules Management server

# Change to the project directory
cd "$(dirname "$0")"

# Activate the virtual environment
source venv-linux/bin/activate

# Set environment variables
export PYTHONPATH="$(pwd)"

# Kill any existing instances
pkill -f "rules_management_server.py" || true

# Create log directory if it doesn't exist
mkdir -p logs

# Make the server script executable
chmod +x rules_management_server.py

# Start the server in the background
nohup python rules_management_server.py > logs/rules_management.log 2>&1 &

# Save the PID
echo $! > rules_management.pid

echo "Rules Management Server started with PID $(cat rules_management.pid)"
echo "Server available at: http://localhost:7890"
echo "Logs available at: $(pwd)/logs/rules_management.log"

# Add a message about MCP integration
echo ""
echo "Note: The Rules Management server works alongside the MCP server."
echo "Make sure the MCP server is running with: ./run_mcp_server.sh"