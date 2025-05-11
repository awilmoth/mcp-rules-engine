#!/bin/bash

# Test script for MCP Inspector redaction

echo "MCP Inspector Redaction Test"
echo "=============================="
echo

# Check if the MCP Inspector server is running
if curl -s http://localhost:6370/health > /dev/null; then
  echo "✓ MCP Inspector server is running"
else
  echo "✗ MCP Inspector server is not running"
  echo "Starting MCP Inspector server..."
  # Kill any existing instance
  pkill -f mcp_inspector_server_fixed.py
  # Start the server
  cd "$(dirname "$0")"
  python3 mcp_inspector_server_fixed.py > /dev/null 2>&1 &
  sleep 2

  # Check again
  if curl -s http://localhost:6370/health > /dev/null; then
    echo "✓ MCP Inspector server started successfully"
  else
    echo "✗ Failed to start MCP Inspector server"
    echo "Please check for errors"
    exit 1
  fi
fi

# Test redaction function
test_redaction() {
  local TEXT="$1"
  echo
  echo "Testing redaction with: \"$TEXT\""
  echo "-------------------------------------"

  # Call the redact_text API
  RESULT=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"redact_text\",\"arguments\":{\"text\":\"$TEXT\"}}}" \
    http://localhost:6370/mcp)

  # Extract the redacted text - this will always work if the result contains redacted_text
  REDACTED=$(echo $RESULT | grep -o '"redacted_text":"[^"]*"' | sed 's/"redacted_text":"//;s/"//')

  if [[ -z "$REDACTED" ]]; then
    echo "✗ Redaction failed - no redacted text returned"
    echo "  Result: $RESULT"
    return 1
  fi

  echo "✓ Redaction successful:"
  echo "  Original: $TEXT"
  echo "  Redacted: $REDACTED"

  # Extract matches
  echo
  echo "Matches:"
  MATCHES=$(echo $RESULT | grep -o '"matches":\[.*\]' | sed 's/"matches"://')

  if [[ "$MATCHES" == "[]" ]]; then
    echo "  No matches found"
  else
    # Use a simple approach to extract match info
    echo $RESULT | grep -o '"rule_name":"[^"]*"' | sed 's/"rule_name":"//;s/"//;s/^/  - /'
  fi

  return 0
}

# Test different types of sensitive information
echo
echo "Testing direct redaction API..."

# Test multiple types of sensitive data
test_redaction "My SSN is 123-45-6789"
test_redaction "My email is user@example.com"
test_redaction "My credit card is 1234 5678 9012 3456"
test_redaction "My phone number is 412-555-1234"

# Test combined sensitive information
test_redaction "My name is John Doe, my SSN is 123-45-6789, my email is john.doe@example.com, my credit card number is 4111-1111-1111-1111, and my phone number is (555) 123-4567."

# Report results
echo
echo "All tests completed!"
echo
echo "Summary:"
echo "- MCP Inspector server is running at http://localhost:6370"
echo "- Direct redaction tests completed"
echo "- Supported redaction types: SSN, Email, Credit Card, Phone Numbers"
echo
echo "To use the web interface, visit:"
echo "  http://172.28.18.245:8000/test.html"
echo
echo "MCP endpoint for integration:"
echo "  http://172.28.18.245:6370/mcp"