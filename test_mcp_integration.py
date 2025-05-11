#!/usr/bin/env python3
import sys
import json
import requests

def test_redact_text():
    """Test the redact_text endpoint directly."""
    url = "http://localhost:6366/redact_text"
    payload = {"text": "My email is example@email.com and my SSN is 123-45-6789"}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Direct Redaction Test - SUCCESS")
            result = response.json()
            print(f"Redacted text: {result['redacted_text']}")
            print(f"Found {len(result['matches'])} matches")
            for match in result['matches']:
                print(f"  - {match['original']} replaced with {match['replacement']} [{match['rule_name']}]")
            return True
        else:
            print(f"Direct Redaction Test - FAILED: HTTP {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Direct Redaction Test - ERROR: {str(e)}")
        return False

def test_mcp_protocol():
    """Test the MCP protocol endpoint."""
    url = "http://localhost:6366/mcp"
    
    # Test with both "legacy" and "tools/call" protocol versions
    for protocol_version in ["legacy", "tools/call"]:
        if protocol_version == "legacy":
            # Legacy protocol format
            payload = {
                "jsonrpc": "2.0",
                "id": "test-1",
                "method": "execute",
                "params": {
                    "name": "redact_text",
                    "parameters": {
                        "text": "My credit card is 1234-5678-9012-3456"
                    }
                }
            }
        else:
            # New protocol format
            payload = {
                "jsonrpc": "2.0",
                "id": "test-2",
                "method": "tools/call",
                "params": {
                    "name": "redact_text",
                    "parameters": {
                        "text": "My credit card is 1234-5678-9012-3456"
                    }
                }
            }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"MCP Protocol Test ({protocol_version}) - SUCCESS")
                result = response.json()
                if "result" in result:
                    redacted = result["result"].get("redacted_text", "No redacted text returned")
                    print(f"Redacted text: {redacted}")
                    matches = result["result"].get("matches", [])
                    print(f"Found {len(matches)} matches")
                    for match in matches:
                        print(f"  - {match.get('original', 'Unknown')} replaced with {match.get('replacement', 'Unknown')}")
                else:
                    print(f"Unexpected response: {json.dumps(result, indent=2)}")
            else:
                print(f"MCP Protocol Test ({protocol_version}) - FAILED: HTTP {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"MCP Protocol Test ({protocol_version}) - ERROR: {str(e)}")

def test_health_endpoints():
    """Test all health endpoints."""
    for endpoint in ["/health", "/healthcheck"]:
        url = f"http://localhost:6366{endpoint}"
        try:
            response = requests.get(url)
            print(f"Health Endpoint {endpoint} - {'SUCCESS' if response.status_code == 200 else 'FAILED'}")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text}")
        except Exception as e:
            print(f"Health Endpoint {endpoint} - ERROR: {str(e)}")

if __name__ == "__main__":
    print("=== MCP Integration Test ===")
    print("\n1. Testing Health Endpoints")
    test_health_endpoints()
    
    print("\n2. Testing Direct Redaction")
    test_redact_text()
    
    print("\n3. Testing MCP Protocol")
    test_mcp_protocol()
    
    print("\n=== Test Complete ===")