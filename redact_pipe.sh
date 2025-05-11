#!/bin/bash

# Script to pipe text through the redaction engine before sending to Claude

# Change to the project directory
cd "$(dirname "$0")"

# Check if Python environment is active
if [ -z "$VIRTUAL_ENV" ]; then
  source venv-linux/bin/activate
fi

# Check for input parameter
if [ $# -eq 0 ]; then
  echo "Usage: $0 \"Your text with sensitive information\""
  echo "Example: $0 \"My SSN is 123-45-6789 and my email is test@example.com\""
  exit 1
fi

# First redact the text
echo "Original text: $1"
echo -e "\nRedacted version:"
REDACTED=$(python redact_text.py "$1")
echo "$REDACTED"

# Then send to Claude
echo -e "\nSending redacted text to Claude:"
claude --print "$REDACTED"