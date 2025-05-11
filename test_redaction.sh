#!/bin/bash

# Test script for MCP rules engine redaction

echo "MCP Rules Engine Redaction Test"
echo "=============================="
echo

# Check if the MCP server is running
if curl -s http://localhost:6366/health > /dev/null; then
  echo "✓ MCP server is running"
else
  echo "✗ MCP server is not running"
  echo "Starting MCP server..."
  ./run_mcp_server.sh
  sleep 2
  
  # Check again
  if curl -s http://localhost:6366/health > /dev/null; then
    echo "✓ MCP server started successfully"
  else
    echo "✗ Failed to start MCP server"
    echo "Please run ./run_mcp_server.sh manually and check for errors"
    exit 1
  fi
fi

# Verify MCP configuration
echo
echo "Checking MCP configuration..."
CLAUDE_CONFIG=$(claude mcp get rules_engine 2>/dev/null)

if [[ -z "$CLAUDE_CONFIG" ]]; then
  echo "✗ Claude MCP configuration not found"
  echo "Configuring Claude with MCP server..."
  
  # Remove any existing configuration
  claude mcp remove rules_engine -s local 2>/dev/null || true
  
  # Add new configuration
  claude mcp add rules_engine http://localhost:6366 --transport sse --scope local
  
  if [ $? -eq 0 ]; then
    echo "✓ MCP configuration added successfully"
  else
    echo "✗ Failed to configure Claude with MCP"
    exit 1
  fi
else
  echo "✓ MCP configuration found"
  echo "$CLAUDE_CONFIG"
fi

# Test direct redaction
echo
echo "Testing direct redaction API..."
TEST_TEXT="My email is test@example.com and my SSN is 123-45-6789"
RESULT=$(curl -s -X POST http://localhost:6366/process_text \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$TEST_TEXT\"}")

PROCESSED_TEXT=$(echo $RESULT | grep -o '"processed_text":"[^"]*"' | sed 's/"processed_text":"//;s/"//')

if [[ "$PROCESSED_TEXT" == *"<EMAIL>"* && "$PROCESSED_TEXT" == *"<SSN>"* ]]; then
  echo "✓ Direct redaction successful:"
  echo "  Original: $TEST_TEXT"
  echo "  Redacted: $PROCESSED_TEXT"
else
  echo "✗ Direct redaction test failed"
  echo "  Result: $RESULT"
  exit 1
fi

# Test with Claude CLI (if available)
echo
echo "Testing with Claude CLI..."
echo "This will attempt to send a message with sensitive info to Claude"
echo "to verify if redaction is working through the MCP integration."
echo
echo -n "Do you want to continue with this test? (y/n): "
read -r CONTINUE

if [[ "$CONTINUE" != "y" ]]; then
  echo "Skipping Claude CLI test"
  echo
  echo "All tests completed!"
  exit 0
fi

# Create a temporary file for Claude input
TEST_PROMPT="Email address: test@example.com
Social Security Number: 123-45-6789
Credit Card: 4111-1111-1111-1111
Phone: (555) 123-4567

Can you see any of the sensitive information above?"

echo "$TEST_PROMPT" > /tmp/test_redaction_input.txt

echo "Sending request to Claude with sensitive information..."
claude --no-stream --model claude-3-5-sonnet-20240620 < /tmp/test_redaction_input.txt

# Clean up
rm /tmp/test_redaction_input.txt

echo
echo "All tests completed!"
echo
echo "Summary:"
echo "- MCP server is running at http://localhost:6366"
echo "- Claude CLI is configured with MCP redaction"
echo "- Direct redaction test successful"
echo 
echo "You can now use Claude with automatic redaction of sensitive information."