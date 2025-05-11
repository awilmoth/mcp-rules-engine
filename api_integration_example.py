#!/usr/bin/env python3
"""
MCP Redaction Integration with Claude API Example

This script demonstrates how to integrate the MCP redaction service 
with the Claude API to automatically redact sensitive information
before sending it to the API.

Note: This is a simplified example that uses mock Claude API calls.
In a real application, you would use the actual Claude API client.
"""

import requests
import json
import sys
import time
import argparse

# MCP Redaction service settings
MCP_BASE_URL = "http://localhost:6366"

# Mock Claude API settings (in a real app, this would be the actual API endpoint)
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_API_KEY = "mock_api_key_for_demo"  # Replace with your actual API key in a real app

class RedactionMiddleware:
    """
    Middleware to redact sensitive information before sending to Claude API.
    """
    
    def __init__(self, mcp_url=MCP_BASE_URL):
        self.mcp_url = mcp_url
        # Check if MCP server is available
        self.server_available = self._check_server()
        if not self.server_available:
            print("Warning: MCP redaction server is not available. Continuing without redaction.")
    
    def _check_server(self):
        """Check if the MCP server is running and healthy."""
        try:
            response = requests.get(f"{self.mcp_url}/health", timeout=3)
            return response.status_code == 200
        except Exception:
            return False
    
    def redact_text(self, text):
        """Redact sensitive information from text using the MCP service."""
        if not self.server_available:
            return text  # Return original text if server is not available
        
        try:
            response = requests.post(
                f"{self.mcp_url}/redact_text",
                json={"text": text},
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            
            # Return redacted text
            return result.get("redacted_text", text)
        except Exception as e:
            print(f"Warning: Error redacting text: {str(e)}")
            return text  # Return original text on error
    
    def get_redactions(self, text):
        """Get the list of redactions that would be applied to the text."""
        if not self.server_available:
            return []
        
        try:
            response = requests.post(
                f"{self.mcp_url}/redact_text",
                json={"text": text},
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            
            # Return list of matches
            return result.get("matches", [])
        except Exception:
            return []

def mock_claude_api_call(messages, model="claude-3-opus-20240229", api_key=CLAUDE_API_KEY):
    """
    Mock Claude API call. In a real application, you would use the Claude API client.
    
    This function simulates the API call and response structure, but doesn't actually
    make a network request to the Claude API.
    """
    print("Sending request to Claude API...")
    print(f"Model: {model}")
    print(f"Message count: {len(messages)}")
    
    # Simulate API delay
    time.sleep(1)
    
    # Simulate API response
    return {
        "id": "msg_" + str(int(time.time())),
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I've processed your request while keeping your information private. "
                        "Since you're using the MCP redaction service, any sensitive information "
                        "like SSNs, credit card numbers, or personal contact details would have been "
                        "automatically redacted before reaching me. This helps protect your privacy while "
                        "still allowing me to provide assistance."
            }
        ],
        "model": model,
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 150,
            "output_tokens": 75
        }
    }

def real_claude_api_call(messages, model="claude-3-opus-20240229", api_key=CLAUDE_API_KEY):
    """
    Make a real Claude API call. This is commented out as it requires a valid API key.
    
    In a real application, you would uncomment this and use your actual API key.
    """
    # Uncomment to use the real API
    """
    import anthropic
    
    client = anthropic.Anthropic(api_key=api_key)
    
    response = client.messages.create(
        model=model,
        messages=messages,
        max_tokens=1000
    )
    
    return response
    """
    
    # For demonstration, we're using the mock instead
    return mock_claude_api_call(messages, model, api_key)

def main():
    parser = argparse.ArgumentParser(description="MCP Redaction Integration with Claude API Example")
    parser.add_argument("-t", "--text", help="Text to redact and send to Claude")
    parser.add_argument("-f", "--file", help="File containing text to redact and send to Claude")
    parser.add_argument("--no-redact", action="store_true", help="Skip redaction (for comparison)")
    parser.add_argument("-m", "--model", default="claude-3-opus-20240229", 
                        help="Claude model to use (default: claude-3-opus-20240229)")
    args = parser.parse_args()
    
    # Get text input
    text = None
    if args.text:
        text = args.text
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            sys.exit(1)
    else:
        # Interactive mode
        print("Enter text to send to Claude (press Ctrl+D when finished):")
        try:
            text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            sys.exit(0)
    
    if not text:
        print("Error: No text provided")
        sys.exit(1)
    
    # Initialize redaction middleware
    middleware = RedactionMiddleware()
    
    # Show original text
    print("\nOriginal text:")
    print("-------------")
    print(text)
    
    if not args.no_redact:
        # Get redactions before applying them
        redactions = middleware.get_redactions(text)
        
        # Apply redaction
        redacted_text = middleware.redact_text(text)
        
        # Show redacted text
        print("\nRedacted text (sent to Claude):")
        print("-----------------------------")
        print(redacted_text)
        
        # Show redactions
        if redactions:
            print("\nRedactions applied:")
            for match in redactions:
                original = match.get("original", "")
                replacement = match.get("replacement", "")
                rule = match.get("rule_name", "Unknown rule")
                print(f"- {original} → {replacement} ({rule})")
        
        # Use redacted text for API call
        text_for_api = redacted_text
    else:
        print("\nSkipping redaction as requested")
        text_for_api = text
    
    # Prepare message for Claude
    messages = [
        {
            "role": "user",
            "content": text_for_api
        }
    ]
    
    # Make the API call
    print("\nCalling Claude API...")
    response = real_claude_api_call(messages, model=args.model)
    
    # Display the response
    print("\nClaude Response:")
    print("---------------")
    
    if isinstance(response, dict) and "content" in response:
        for content in response["content"]:
            if content.get("type") == "text":
                print(content.get("text", ""))
    else:
        print(str(response))
    
    # Display token usage
    if isinstance(response, dict) and "usage" in response:
        usage = response["usage"]
        print(f"\nToken usage: {usage.get('input_tokens', 0)} input, {usage.get('output_tokens', 0)} output")

if __name__ == "__main__":
    main()