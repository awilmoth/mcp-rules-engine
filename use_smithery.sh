#!/bin/bash
# Script to set up and use Smithery AI integration with Claude

# Change to the project directory
cd "$(dirname "$0")"

# Make sure we have a virtual environment activated
if [ -z "$VIRTUAL_ENV" ]; then
  source venv-linux/bin/activate
fi

# Check if smithery_config.json exists, create if not
if [ ! -f smithery_config.json ]; then
  echo "Creating default Smithery configuration..."
  cat > smithery_config.json << EOF
{
  "local_mcp_url": "http://localhost:6366",
  "smithery_api_url": "https://api.smithery.ai/v1",
  "smithery_api_key": "",
  "use_local_fallback": true
}
EOF
fi

# Make sure the integration script is executable
chmod +x smithery_integration.py

# Function to display help
show_help() {
  echo "Smithery AI Integration for Claude"
  echo ""
  echo "Usage:"
  echo "  $0 configure           Configure Smithery API integration"
  echo "  $0 redact [text]       Redact text using Smithery (or local fallback)"
  echo "  $0 claude [text]       Redact text and send to Claude"
  echo ""
  echo "Examples:"
  echo "  $0 configure                         Configure Smithery integration"
  echo "  $0 redact \"My SSN is 123-45-6789\"    Redact sensitive information"
  echo "  $0 claude \"My credit card: 4111-1111-1111-1111\"  Redact and send to Claude"
  echo ""
  echo "If no text is provided, the script will read from standard input."
}

# Check command
if [ "$1" == "configure" ]; then
  # Configure Smithery integration
  ./smithery_integration.py configure
elif [ "$1" == "redact" ]; then
  # Redact text
  if [ -n "$2" ]; then
    # Use provided text
    ./smithery_integration.py redact --text "$2"
  else
    # Read from stdin
    cat | ./smithery_integration.py redact
  fi
elif [ "$1" == "claude" ]; then
  # Redact and send to Claude
  if [ -n "$2" ]; then
    # Use provided text
    ./smithery_integration.py claude --text "$2"
  else
    # Read from stdin
    cat | ./smithery_integration.py claude
  fi
else
  # Show help
  show_help
fi