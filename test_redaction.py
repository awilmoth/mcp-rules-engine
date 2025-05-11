#!/usr/bin/env python3
import requests
import json
import sys

def test_direct_redaction():
    """Test the redaction endpoint with various sensitive information patterns."""
    url = "http://localhost:6366/redact_text"
    
    test_cases = [
        {
            "name": "SSN Test",
            "text": "My social security number is 123-45-6789.",
            "expected_pattern": "<SSN>"
        },
        {
            "name": "Email Test",
            "text": "Please contact me at john.doe@example.com for more information.",
            "expected_pattern": "<EMAIL>"
        },
        {
            "name": "Credit Card Test",
            "text": "My credit card is 4111-1111-1111-1111 and expires 12/25.",
            "expected_pattern": "<CREDIT_CARD>"
        },
        {
            "name": "Phone Number Test",
            "text": "Call me at (555) 123-4567 or +1 555-987-6543.",
            "expected_pattern": "<PHONE>"
        },
        {
            "name": "Credentials Test",
            "text": "api_key=1234567890abcdef password: supersecret123",
            "expected_pattern": "<CREDENTIAL>"
        },
        {
            "name": "Multiple Patterns Test",
            "text": "Name: John Doe\nEmail: john@example.com\nPhone: (555) 123-4567\nSSN: 123-45-6789\nCC: 4111-1111-1111-1111",
            "expected_pattern": "multiple patterns"
        }
    ]
    
    print("Testing Rules Engine Redaction Capabilities\n")
    
    success_count = 0
    failure_count = 0
    
    for test in test_cases:
        print(f"Test: {test['name']}")
        print(f"Input: {test['text']}")
        
        data = {
            "text": test['text']
        }
        
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                result = response.json()
                # Handle different response formats
                redacted_text = result.get('redacted_text', result.get('text', ''))
                print(f"Output: {redacted_text}")
                
                # Check if redaction occurred
                if test['expected_pattern'] == "multiple patterns":
                    # For multiple pattern test, just check if text was changed
                    if redacted_text != test['text']:
                        print("✅ Success: Multiple patterns redacted\n")
                        success_count += 1
                    else:
                        print("❌ Failure: No redaction occurred\n")
                        failure_count += 1
                else:
                    # For single pattern test, check if expected pattern is in the output
                    if test['expected_pattern'] in redacted_text:
                        print(f"✅ Success: Found redacted pattern {test['expected_pattern']}\n")
                        success_count += 1
                    else:
                        print(f"❌ Failure: Expected pattern {test['expected_pattern']} not found\n")
                        failure_count += 1
            else:
                print(f"❌ Error: Server returned status code {response.status_code}")
                print(response.text)
                failure_count += 1
                
        except Exception as e:
            print(f"❌ Error connecting to server: {str(e)}")
            failure_count += 1
    
    # Print summary
    total = success_count + failure_count
    print(f"Summary: {success_count}/{total} tests passed")
    
    if success_count == total:
        print("All tests passed! The rules engine is working correctly.")
        return True
    else:
        print(f"Some tests failed. {failure_count} issues need to be fixed.")
        return False

def test_mcp_endpoints():
    """Test the available MCP API endpoints"""
    base_url = "http://localhost:6366"
    
    endpoints = [
        {"path": "/health", "method": "GET", "name": "Health Check"},
        {"path": "/sse", "method": "GET", "name": "SSE Connection", "skip_test": True},
        {"path": "/redact_text", "method": "POST", "data": {"text": "Test SSN: 123-45-6789"}, "name": "Redact Text"},
        {"path": "/mcp", "method": "POST", "data": {"text": "Test SSN: 123-45-6789", "tool": "redact_text"}, "name": "MCP Protocol"}
    ]
    
    print("\nTesting MCP API Endpoints\n")
    
    for ep in endpoints:
        if ep.get("skip_test"):
            print(f"Skipping {ep['name']} endpoint ({ep['path']})")
            continue
            
        print(f"Testing {ep['name']} endpoint ({ep['path']})")
        
        try:
            if ep["method"] == "GET":
                response = requests.get(f"{base_url}{ep['path']}")
            else:
                response = requests.post(f"{base_url}{ep['path']}", json=ep.get("data", {}))
                
            print(f"Status: {response.status_code}")
            
            if response.status_code < 400:
                print(f"✅ Success: {ep['name']} endpoint is working")
                try:
                    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
                except:
                    print(f"Response: {response.text[:100]}...\n")
            else:
                print(f"❌ Error: {ep['name']} endpoint returned {response.status_code}")
                print(f"Response: {response.text}\n")
                
        except Exception as e:
            print(f"❌ Error connecting to {ep['path']}: {str(e)}\n")

if __name__ == "__main__":
    print("Testing MCP redaction functionality...")
    
    # Test available endpoints
    test_mcp_endpoints()
    
    # Test redaction functionality
    success = test_direct_redaction()
    
    if not success:
        print("Redaction tests failed. Review server configuration.")
        sys.exit(1)
    
    print("Redaction tests completed successfully.")
    sys.exit(0)