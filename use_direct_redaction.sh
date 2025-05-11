#!/bin/bash

# Script to set up a Claude input pipeline with redaction

# Change to the project directory
cd "$(dirname "$0")"

# Make sure we have a virtual environment activated
if [ -z "$VIRTUAL_ENV" ]; then
  source venv-linux/bin/activate
fi

# Make sure the MCP server is running
if ! curl -s http://localhost:6366/health > /dev/null; then
  echo "MCP server is not running. Starting it..."
  ./run_mcp_server.sh
  
  # Wait a moment for the server to start
  sleep 2
fi

# Create a pipe function for redaction
redact_stdin() {
  while IFS= read -r line; do
    if [ -n "$line" ]; then
      # Send to redaction API
      redacted=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "{\"text\": \"$line\"}" \
        http://localhost:6366/redact_text | jq -r '.redacted_text')
      
      # Output redacted text
      echo "$redacted"
    else
      # Pass through empty lines
      echo ""
    fi
  done
}

# Check if we have arguments
if [ $# -eq 0 ]; then
  # Interactive mode
  echo "=== Claude with Redaction ==="
  echo "Type your messages, they will be automatically redacted before being sent to Claude."
  echo "Type 'exit' to quit."
  
  # Start interactive mode
  while true; do
    # Prompt for input
    echo -n "> "
    read -r input
    
    # Exit if requested
    if [ "$input" = "exit" ]; then
      break
    fi
    
    # Redact input
    redacted=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "{\"text\": \"$input\"}" \
        http://localhost:6366/redact_text | jq -r '.redacted_text')
    
    # Show what was redacted
    if [ "$input" != "$redacted" ]; then
      echo "Redacted: $redacted"
    fi
    
    # Send to Claude
    echo -e "\nClaude response:"
    echo "$redacted" | claude --print
    echo
  done
else
  # Direct mode: redact the argument and send to Claude
  echo "Original: $1"
  redacted=$(curl -s -X POST -H "Content-Type: application/json" \
      -d "{\"text\": \"$1\"}" \
      http://localhost:6366/redact_text | jq -r '.redacted_text')
  
  echo "Redacted: $redacted"
  echo -e "\nClaude response:"
  claude --print "$redacted"
fi