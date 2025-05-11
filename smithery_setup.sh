#!/bin/bash
# Updated Smithery CLI integration for MCP Rules Engine

# Change to the project directory
cd "$(dirname "$0")"

# Make sure we have a virtual environment activated
if [ -z "$VIRTUAL_ENV" ]; then
  source venv-linux/bin/activate
fi

# Check arguments
if [ "$1" == "--help" ] || [ "$1" == "-h" ] || [ -z "$1" ]; then
  echo "Smithery CLI Setup for MCP Rules Engine"
  echo ""
  echo "Usage:"
  echo "  $0 install [API_KEY]     - Install MCP server to Smithery"
  echo "  $0 run                   - Run local MCP server with Smithery"
  echo "  $0 list                  - List available clients and installed servers"
  echo "  $0 test [TEXT]           - Test redaction through Smithery"
  echo ""
  echo "Examples:"
  echo "  $0 install ant-xxxxxxxxxxxxxxxxxxxxxxxx"
  echo "  $0 run"
  echo "  $0 test \"My SSN is 123-45-6789\""
  exit 0
fi

# Run the correct command based on the first argument
case "$1" in
  install)
    # Check for API key
    if [ -z "$2" ]; then
      echo "Error: API key required for installation"
      echo "Usage: $0 install YOUR_API_KEY"
      exit 1
    fi
    
    API_KEY="$2"
    
    echo "Installing MCP Rules Engine to Smithery..."
    echo ""
    
    # Prepare package if needed
    if [ ! -f "rules_engine_mcp.zip" ]; then
      echo "Creating deployment package..."
      ./prepare_smithery_deployment.sh
    fi
    
    # Install MCP server to Smithery
    echo "Installing server with Smithery CLI..."
    npx -y @smithery/cli@latest install ./rules_engine_mcp.zip --key "$API_KEY"
    
    # Connect to Claude client
    echo ""
    echo "Connecting to Claude client..."
    npx -y @smithery/cli@latest install @smithery/claude-connector --key "$API_KEY"
    
    echo ""
    echo "Installation complete. You can now run 'smithery_setup.sh run' to start the server"
    ;;
    
  run)
    echo "Running MCP Rules Engine with Smithery integration..."
    
    # Check for local server configuration
    if [ ! -f "smithery.json" ]; then
      echo "Error: smithery.json not found"
      echo "Run ./prepare_smithery_deployment.sh first to create the configuration"
      exit 1
    fi
    
    # Run the server using Smithery CLI
    npx -y @smithery/cli@latest run ./smithery.json
    ;;
    
  list)
    echo "Listing Smithery information..."
    echo ""
    echo "Available clients:"
    npx -y @smithery/cli@latest list clients
    
    echo ""
    echo "Installed servers:"
    npx -y @smithery/cli@latest list servers
    ;;
    
  test)
    # Check for test text
    if [ -z "$2" ]; then
      echo "Error: No text provided for testing"
      echo "Usage: $0 test \"Text to redact\""
      exit 1
    fi
    
    TEST_TEXT="$2"
    
    echo "Testing redaction with Smithery integration..."
    echo ""
    echo "Input: $TEST_TEXT"
    echo ""
    
    # Run through local MCP server first
    echo "Local MCP redaction:"
    REDACTED=$(curl -s -X POST -H "Content-Type: application/json" \
      -d "{\"text\": \"$TEST_TEXT\"}" \
      http://localhost:6366/redact_text | jq -r '.redacted_text')
    echo "$REDACTED"
    
    echo ""
    echo "To test with Smithery-hosted server, use Claude with the Smithery integration"
    echo "Via API: curl -H \"Authorization: Bearer API_KEY\" https://api.smithery.ai/v1/claude/text -d '{\"text\":\"$TEST_TEXT\"}'"
    ;;
    
  *)
    echo "Unknown command: $1"
    echo "Run '$0 --help' for usage information"
    exit 1
    ;;
esac