#!/usr/bin/env python3
import subprocess
import sys
import json
import time
import os

def run_cmd(cmd):
    """Run a command and return output."""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        print(f"STDERR: {e.stderr}")
        return None

def check_mcp_server():
    """Check if MCP server is running."""
    try:
        result = subprocess.run(['curl', '-s', 'http://localhost:6366/health'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and 'ok' in result.stdout:
            print("✅ MCP server is running")
            return True
        else:
            print("❌ MCP server is not responding")
            return False
    except Exception as e:
        print(f"❌ Error checking MCP server: {e}")
        return False

def check_mcp_config():
    """Check Claude MCP configuration."""
    result = run_cmd("claude mcp get rules_engine")
    if result:
        if "URL: http://localhost:6366" in result and "Type: sse" in result:
            print("✅ Claude MCP is configured correctly with SSE transport")
            return True
        else:
            print("❌ Claude MCP configuration is incorrect")
            print(result)
            return False
    return False

def test_mcp_functionality():
    """Test MCP functionality with direct API calls."""
    print("\nTesting MCP redaction functionality directly...\n")

    # Test text with sensitive information
    test_text = """
    Here is some sensitive information:
    - Email: test@example.com
    - SSN: 123-45-6789
    - Credit Card: 4111-1111-1111-1111
    - Phone: (555) 123-4567
    """

    # Use curl to test redaction API directly
    print("Testing direct redaction API...")
    # Create a clean JSON input
    test_data = {
        "text": "My SSN is 123-45-6789 and my credit card is 4111-1111-1111-1111. My email is test@example.com."
    }
    json_str = json.dumps(test_data)
    curl_cmd = f'curl -s -X POST -H "Content-Type: application/json" -d \'{json_str}\' http://localhost:6366/redact_text'
    result = run_cmd(curl_cmd)

    if result:
        try:
            data = json.loads(result)
            print("\nAPI response:")
            print("---------------")
            print(f"Redacted text: {data['redacted_text']}")
            print("\nRedacted items:")
            for match in data['matches']:
                print(f"- {match['original']} → {match['replacement']} ({match['rule_name']})")

            if len(data['matches']) > 0:
                print("\n✅ MCP redaction is working properly")
                return True
            else:
                print("\n❌ No items were redacted")
                return False
        except json.JSONDecodeError:
            print(f"\n❌ Invalid JSON response: {result}")
            return False
        except KeyError as e:
            print(f"\n❌ Missing expected key in response: {e}")
            return False

    print("\n❌ Failed to get response from redaction API")
    return False

def main():
    """Main test function."""
    print("Claude MCP Integration Test")
    print("==========================\n")
    
    # Check if MCP server is running
    if not check_mcp_server():
        print("\n❌ MCP server is not running. Start it with:")
        print("   ./run_mcp_server.sh")
        return False
    
    # Check MCP configuration
    if not check_mcp_config():
        print("\n❌ MCP configuration is incorrect. Fix it with:")
        print("   claude mcp remove rules_engine -s local")
        print("   claude mcp add rules_engine http://localhost:6366 --transport sse --scope local")
        return False
    
    # Test MCP functionality directly
    test_mcp_functionality()
    
    print("\nTest completed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)