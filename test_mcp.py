#!/usr/bin/env python3
import requests
import json
import sys

def test_redact_text(text):
    """Test the redact_text endpoint directly."""
    try:
        response = requests.post(
            "http://localhost:6366/redact_text",
            json={"text": text},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        print("\nDirect API Test:")
        print(f"Original: {text}")
        print(f"Redacted: {result['redacted_text']}")
        print("Matches:", json.dumps(result["matches"], indent=2))
        return result
    except Exception as e:
        print(f"Error testing redact_text: {str(e)}")
        return None

def test_mcp_rpc(text):
    """Test the MCP RPC endpoint."""
    try:
        response = requests.post(
            "http://localhost:6366/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "redact_text",
                "params": {"text": text}
            },
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        print("\nMCP RPC Test:")
        print(f"Original: {text}")
        if "result" in result:
            print(f"Redacted: {result['result']['redacted_text']}")
            print("Matches:", json.dumps(result["result"]["matches"], indent=2))
        else:
            print("Error:", result.get("error", "Unknown error"))
        return result
    except Exception as e:
        print(f"Error testing MCP RPC: {str(e)}")
        return None

def test_tools_call(text):
    """Test the tools/call RPC endpoint."""
    try:
        response = requests.post(
            "http://localhost:6366/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "redact_text",
                    "parameters": {"text": text}
                }
            },
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        print("\ntools/call RPC Test:")
        print(f"Original: {text}")
        if "result" in result:
            print(f"Redacted: {result['result']['redacted_text']}")
            print("Matches:", json.dumps(result["result"]["matches"], indent=2))
        else:
            print("Error:", result.get("error", "Unknown error"))
        return result
    except Exception as e:
        print(f"Error testing tools/call: {str(e)}")
        return None

def check_server_health():
    """Check if the server is running."""
    try:
        response = requests.get("http://localhost:6366/health")
        response.raise_for_status()
        print("Server status:", response.json())
        return True
    except Exception as e:
        print(f"Error: Server not available - {str(e)}")
        return False

def list_mcp_tools():
    """List available MCP tools."""
    try:
        response = requests.get("http://localhost:6366/mcp-tools")
        response.raise_for_status()
        tools = response.json().get("tools", [])
        print("\nAvailable MCP tools:")
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")
            print(f"  Parameters: {json.dumps(tool['parameters'], indent=2)}")
        return tools
    except Exception as e:
        print(f"Error listing tools: {str(e)}")
        return []

if __name__ == "__main__":
    print("MCP Server Test")
    print("===============")
    
    # Check if server is running
    if not check_server_health():
        sys.exit(1)
    
    # List available tools
    list_mcp_tools()
    
    # Test text with various sensitive information
    test_text = """
    My SSN is 123-45-6789 and my credit card is 4111-1111-1111-1111.
    Please contact me at test@example.com or call 555-123-4567.
    The server IP is 192.168.1.1 and the API key is api_key=abcd1234.
    """
    
    # Test direct endpoint
    test_redact_text(test_text)
    
    # Test MCP RPC endpoint
    test_mcp_rpc(test_text)
    
    # Test tools/call endpoint
    test_tools_call(test_text)
    
    print("\nAll tests completed.")