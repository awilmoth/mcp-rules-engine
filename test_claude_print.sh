#!/bin/bash

# Set the test message with sensitive info
TEST_MESSAGE="My SSN is 123-45-6789 and my credit card is 4111-1111-1111-1111. My email is test@example.com."

echo "Testing Claude with --print flag and MCP redaction"
echo "=================================================="
echo 
echo "Test message: $TEST_MESSAGE"
echo
echo "Sending to Claude with MCP integration enabled..."
echo

# Write message to temp file to handle special characters
echo "$TEST_MESSAGE" > temp_message.txt

# Run Claude with --print flag, reading from the temp file
claude -p "$(cat temp_message.txt)"

echo
echo "Test completed."