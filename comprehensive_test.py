#!/usr/bin/env python3
"""
Comprehensive MCP Rules Engine Test Suite
This script tests all aspects of the MCP Rules Engine integration.
"""

import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime

# Define colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(title):
    """Print a formatted header."""
    print(f"\n{BOLD}{'=' * 80}{RESET}")
    print(f"{BOLD}{title.center(80)}{RESET}")
    print(f"{BOLD}{'=' * 80}{RESET}\n")

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{BOLD}{title}{RESET}")
    print(f"{BOLD}{'-' * len(title)}{RESET}")

def print_result(test_name, success, message=""):
    """Print a formatted test result."""
    if success:
        print(f"{GREEN}✓ {test_name}{RESET} {message}")
    else:
        print(f"{RED}✗ {test_name}{RESET} {message}")
    return success

def run_command(cmd, capture=True, print_output=False):
    """Run a shell command and return the output."""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, check=False, 
                               capture_output=True, text=True)
            if print_output and result.stdout:
                print(result.stdout)
            if print_output and result.stderr:
                print(f"{RED}{result.stderr}{RESET}")
            return result
        else:
            return subprocess.run(cmd, shell=True, check=False)
    except Exception as e:
        print(f"{RED}Error executing command: {cmd}{RESET}")
        print(f"{RED}{str(e)}{RESET}")
        return None

def test_mcp_server_running():
    """Test if the MCP server is running."""
    print_section("MCP Server Status")
    
    try:
        response = requests.get("http://localhost:6366/health", timeout=5)
        if response.status_code == 200:
            return print_result("MCP server is running", True, f"at http://localhost:6366")
        else:
            return print_result("MCP server is not running", False, f"HTTP status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        return print_result("MCP server is not running", False, "Connection error")
    except Exception as e:
        return print_result("Error checking MCP server", False, str(e))

def start_mcp_server():
    """Start the MCP server."""
    print_section("Starting MCP Server")
    
    result = run_command("./run_mcp_server.sh", print_output=True)
    if result and result.returncode == 0:
        # Wait for server to start up
        time.sleep(2)
        return test_mcp_server_running()
    else:
        return print_result("Failed to start MCP server", False)

def test_claude_mcp_config():
    """Test Claude CLI MCP configuration."""
    print_section("Claude MCP Configuration")
    
    result = run_command("claude mcp get rules_engine")
    if not result or result.returncode != 0:
        return print_result("Claude MCP config not found", False)
    
    output = result.stdout
    print(output)
    
    # Check if using SSE transport
    if "Type: sse" in output and "http://localhost:6366" in output:
        return print_result("Claude MCP is correctly configured", True, "using SSE transport")
    else:
        return print_result("Claude MCP has incorrect configuration", False)

def configure_claude_mcp():
    """Configure Claude CLI with MCP."""
    print_section("Configuring Claude MCP")
    
    # Remove any existing configuration
    run_command("claude mcp remove rules_engine -s local 2>/dev/null || true")
    
    # Add new configuration with SSE transport
    result = run_command("claude mcp add rules_engine http://localhost:6366 --transport sse --scope local")
    if result and result.returncode == 0:
        return test_claude_mcp_config()
    else:
        return print_result("Failed to configure Claude MCP", False)

def test_redaction_api(verbose=True):
    """Test the direct redaction API."""
    print_section("Direct Redaction API Test")
    
    # Test data
    test_data = {
        "Email": "test@example.com",
        "SSN": "123-45-6789",
        "Credit Card": "4111-1111-1111-1111",
        "Phone": "(555) 123-4567",
        "API Key": "api_key=abcdef123456",
        "IP Address": "192.168.1.1"
    }
    
    # Build test text
    test_text = "Here's some sensitive information:\n"
    for key, value in test_data.items():
        test_text += f"{key}: {value}\n"
    
    try:
        response = requests.post(
            "http://localhost:6366/process_text",
            headers={"Content-Type": "application/json"},
            json={"text": test_text},
            timeout=5
        )
        
        if response.status_code != 200:
            return print_result("Redaction API test failed", False, f"HTTP status: {response.status_code}")
        
        result = response.json()
        processed_text = result.get("processed_text", "")
        results = result.get("results", [])
        
        # Print results
        if verbose:
            print(f"\nOriginal text:\n{YELLOW}{test_text}{RESET}")
            print(f"\nRedacted text:\n{YELLOW}{processed_text}{RESET}")
            print(f"\nRedaction results:")
            for item in results:
                action = item.get("action", "unknown")
                original = item.get("original", "unknown")
                replacement = item.get("replacement", "unknown")
                rule_name = item.get("rule_name", "unknown")
                print(f"  - {YELLOW}{original}{RESET} → {GREEN}{replacement}{RESET} [{rule_name}]")
        
        # Check if all sensitive data was redacted
        success = True
        for key, value in test_data.items():
            if value in processed_text:
                print(f"{RED}✗ {key} was not redacted: {value}{RESET}")
                success = False
        
        return print_result(
            "Redaction API test", 
            success,
            f"({len(results)} items redacted)"
        )
    except Exception as e:
        return print_result("Redaction API test failed", False, str(e))

def test_mcp_protocol():
    """Test the MCP protocol endpoints."""
    print_section("MCP Protocol Test")
    
    success = True
    
    # Test with both legacy and tools/call protocol versions
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
            response = requests.post(
                "http://localhost:6366/mcp",
                json=payload,
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"{RED}✗ MCP Protocol ({protocol_version}) failed{RESET} - HTTP {response.status_code}")
                success = False
                continue
            
            result = response.json()
            if "result" not in result:
                print(f"{RED}✗ MCP Protocol ({protocol_version}) failed{RESET} - No result in response")
                success = False
                continue
            
            redacted = result["result"].get("redacted_text", "")
            matches = result["result"].get("matches", [])
            
            # Check if credit card was redacted
            if "1234-5678-9012-3456" not in redacted and "<CREDIT_CARD>" in redacted:
                print(f"{GREEN}✓ MCP Protocol ({protocol_version}){RESET} - Redaction successful")
                print(f"  Redacted: {redacted}")
                print(f"  Found {len(matches)} matches")
            else:
                print(f"{RED}✗ MCP Protocol ({protocol_version}) failed{RESET} - Redaction not working")
                success = False
                
        except Exception as e:
            print(f"{RED}✗ MCP Protocol ({protocol_version}) failed{RESET} - {str(e)}")
            success = False
    
    return success

def create_test_file():
    """Create a test file with sensitive information."""
    test_content = """To: security@example.com
From: admin@example.com
Subject: Security test

Please redact the following sensitive information:

1. Credit Card: 4111-1111-1111-1111
2. SSN: 123-45-6789
3. API Key: api_key=abcdef123456
4. Phone: (555) 123-4567
5. IP Address: 192.168.1.1

This is a test for the MCP redaction engine.
"""
    
    try:
        with open("test_sensitive_data.txt", "w") as f:
            f.write(test_content)
        return True
    except Exception as e:
        print(f"{RED}Error creating test file: {str(e)}{RESET}")
        return False

def run_all_tests():
    """Run all tests and return overall success status."""
    print_header("MCP Rules Engine Comprehensive Test")
    
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Running tests from: {os.getcwd()}")
    
    # Test if MCP server is running
    server_running = test_mcp_server_running()
    
    # Start server if not running
    if not server_running:
        server_running = start_mcp_server()
        if not server_running:
            print(f"\n{RED}Cannot proceed with tests - MCP server failed to start{RESET}")
            return False
    
    # Test Claude MCP configuration
    config_ok = test_claude_mcp_config()
    
    # Configure if not correctly set up
    if not config_ok:
        config_ok = configure_claude_mcp()
        if not config_ok:
            print(f"\n{YELLOW}Warning: Claude MCP configuration issues may affect redaction{RESET}")
    
    # Test direct redaction API
    redaction_ok = test_redaction_api()
    
    # Test MCP protocol
    protocol_ok = test_mcp_protocol()
    
    # Create test file for manual testing
    create_test_file()
    
    # Summary
    print_section("Test Summary")
    
    print(f"MCP Server: {'✓' if server_running else '✗'}")
    print(f"Claude Configuration: {'✓' if config_ok else '✗'}")
    print(f"Redaction API: {'✓' if redaction_ok else '✗'}")
    print(f"MCP Protocol: {'✓' if protocol_ok else '✗'}")
    
    all_tests_passed = server_running and config_ok and redaction_ok and protocol_ok
    
    if all_tests_passed:
        print(f"\n{GREEN}{BOLD}All tests passed!{RESET}")
        print(f"\nYou can now use Claude with automatic redaction of sensitive information.")
        print(f"A test file with sensitive data has been created: {YELLOW}test_sensitive_data.txt{RESET}")
    else:
        print(f"\n{YELLOW}{BOLD}Some tests failed.{RESET}")
        print(f"Review the output above and fix any issues.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)