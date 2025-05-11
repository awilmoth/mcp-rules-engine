#!/bin/bash
# Run all MCP Rules Engine tests

# Navigate to script directory
cd "$(dirname "$0")"

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print header
echo -e "${BOLD}MCP Rules Engine Test Suite${NC}"
echo "=============================="
echo

# 1. Start the MCP server if not running
if ! curl -s http://localhost:6366/health > /dev/null; then
  echo -e "${YELLOW}MCP server not running. Starting...${NC}"
  ./run_mcp_server.sh
  sleep 2
  
  if ! curl -s http://localhost:6366/health > /dev/null; then
    echo -e "${RED}Failed to start MCP server. Tests cannot proceed.${NC}"
    exit 1
  fi
  echo -e "${GREEN}MCP server started successfully!${NC}"
else
  echo -e "${GREEN}MCP server already running${NC}"
fi

# 2. Configure Claude MCP
echo
echo "Configuring Claude MCP..."
claude mcp remove rules_engine -s local 2>/dev/null || true
claude mcp add rules_engine http://localhost:6366 --transport sse --scope local

if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to configure Claude MCP${NC}"
  exit 1
else
  echo -e "${GREEN}Claude MCP configured successfully!${NC}"
fi

# 3. Run basic redaction test
echo
echo "Running basic redaction test..."
./test_redaction.sh

# 4. Run integration test
echo
echo "Running integration test..."
source venv-linux/bin/activate
python test_mcp_integration.py

# 5. Run comprehensive test
echo
echo "Running comprehensive tests..."
python comprehensive_test.py

# Done
echo
echo -e "${BOLD}Test suite complete!${NC}"
echo
echo "Next steps:"
echo "1. Use Claude with automatic redaction: ${BOLD}claude${NC}"
echo "2. For manual testing: ${BOLD}cat test_sensitive_data.txt | claude${NC}"
echo
echo "See README_MCP_USAGE.md for more information"