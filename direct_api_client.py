#!/usr/bin/env python3
"""
MCP Redaction API Client

This script demonstrates how to use the MCP Redaction API endpoints directly
for programmatic access to the redaction service.
"""

import requests
import json
import sys
import argparse

API_BASE_URL = "http://localhost:6366"

def check_server():
    """Check if the MCP server is running and healthy."""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            return True
        return False
    except Exception:
        return False

def redact_text(text):
    """Redact sensitive information from text using the direct API."""
    if not text:
        print("Error: No text provided for redaction")
        return None
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/redact_text",
            json={"text": text},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error redacting text: {str(e)}")
        return None

def process_text(text, rule_sets=None):
    """Process text with more options using the process_text endpoint."""
    if not text:
        print("Error: No text provided for processing")
        return None
    
    data = {"text": text}
    if rule_sets:
        data["rule_sets"] = rule_sets
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/process_text",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error processing text: {str(e)}")
        return None

def list_tools():
    """List available MCP tools."""
    try:
        response = requests.get(f"{API_BASE_URL}/mcp-tools")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error listing tools: {str(e)}")
        return None

def rpc_call(method, params=None):
    """Make a generic RPC call to the MCP server."""
    if params is None:
        params = {}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            },
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error making RPC call: {str(e)}")
        return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Redaction API Client")
    parser.add_argument("-t", "--text", help="Text to redact")
    parser.add_argument("-f", "--file", help="File containing text to redact")
    parser.add_argument("-l", "--list-tools", action="store_true", help="List available MCP tools")
    parser.add_argument("-o", "--output", help="Output file for redacted text")
    parser.add_argument("--json", action="store_true", help="Output full JSON response")
    args = parser.parse_args()
    
    # Check if server is running
    if not check_server():
        print("Error: MCP server is not running. Start it with run_mcp_server.sh")
        sys.exit(1)
    
    # List tools if requested
    if args.list_tools:
        tools = list_tools()
        if tools:
            print("Available MCP tools:")
            for tool in tools.get("tools", []):
                print(f"\n- {tool['name']}: {tool['description']}")
                print("  Parameters:")
                for param_name, param in tool.get("parameters", {}).items():
                    print(f"    - {param_name}: {param.get('description', '')}")
        sys.exit(0)
    
    # Get text to redact
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
        print("Enter text to redact (press Ctrl+D when finished):")
        try:
            text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            sys.exit(0)
    
    if not text:
        print("Error: No text provided for redaction")
        sys.exit(1)
    
    # Redact text
    result = redact_text(text)
    
    if not result:
        print("Error: Failed to redact text")
        sys.exit(1)
    
    # Process the result
    if args.json:
        # Output full JSON response
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))
    else:
        # Output just the redacted text
        redacted_text = result.get("redacted_text", "")
        matches = result.get("matches", [])
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(redacted_text)
        else:
            print("\nOriginal text:")
            print("-------------")
            print(text)
            print("\nRedacted text:")
            print("-------------")
            print(redacted_text)
            
            # Show redaction details
            if matches:
                print("\nRedactions applied:")
                for match in matches:
                    original = match.get("original", "")
                    replacement = match.get("replacement", "")
                    rule = match.get("rule_name", "Unknown rule")
                    print(f"- {original} → {replacement} ({rule})")
            else:
                print("\nNo redactions were applied.")

if __name__ == "__main__":
    main()