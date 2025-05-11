#!/bin/bash
# Deploy the Rules Management server to Smithery

# Change to the project directory
cd "$(dirname "$0")"

# Make sure npm and the Smithery CLI are installed
if ! command -v npx &> /dev/null; then
    echo "Error: npx is not installed. Please install Node.js and npm."
    exit 1
fi

# Install Smithery CLI if needed
npx -y @smithery/cli@latest --version || npm install -g @smithery/cli

# Check if MCP server is running
if ! curl -s http://localhost:6366/health &> /dev/null; then
    echo "Warning: MCP server is not running. Starting it now..."
    ./run_mcp_server.sh
    # Wait for the server to start
    sleep 3
fi

# Test MCP connectivity
if ! curl -s http://localhost:6366/health &> /dev/null; then
    echo "Error: Failed to connect to MCP server. Please make sure it's running."
    exit 1
fi

echo "MCP server is running and healthy."

# Check if the rules management server is running
if ! curl -s http://localhost:7890 &> /dev/null; then
    echo "Warning: Rules Management server is not running. Starting it now..."
    ./run_rules_management.sh
    # Wait for the server to start
    sleep 3
fi

# Test Rules Management connectivity
if ! curl -s http://localhost:7890 &> /dev/null; then
    echo "Error: Failed to connect to Rules Management server. Please make sure it's running."
    exit 1
fi

echo "Rules Management server is running and healthy."

# Deploy to Smithery
echo "Deploying to Smithery..."
npx @smithery/cli install @awilmoth/mcp-rules-engine --client claude --key "b0074679-8be8-4622-9faf-ebee3f46a830"

echo "Deployment complete!"
echo "You can now access your service through Claude Code."