#!/usr/bin/env python3
"""
Smithery AI Integration for MCP Redaction

This script provides a bridge between Smithery AI's data protection
and the local MCP redaction engine.
"""

import os
import sys
import json
import requests
import argparse
import logging
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmitheryIntegration")

# Default configuration
DEFAULT_CONFIG = {
    "local_mcp_url": "http://localhost:6366",
    "smithery_api_url": "https://api.smithery.ai/v1",
    "smithery_api_key": "",  # To be configured by user
    "use_local_fallback": True
}

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file or use defaults."""
    config = DEFAULT_CONFIG.copy()
    
    # Determine config path
    if not config_path:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                 "smithery_config.json")
    
    # Load config if it exists
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
    else:
        logger.warning(f"Configuration file not found: {config_path}")
        
    # Check for environment variables
    if "SMITHERY_API_KEY" in os.environ:
        config["smithery_api_key"] = os.environ["SMITHERY_API_KEY"]
        
    return config

def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> bool:
    """Save configuration to file."""
    if not config_path:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                 "smithery_config.json")
    
    try:
        # Create a copy without API key for security
        save_config = config.copy()
        if "smithery_api_key" in save_config:
            save_config["smithery_api_key"] = ""  # Don't save API key to disk
            
        with open(config_path, 'w') as f:
            json.dump(save_config, f, indent=2)
        logger.info(f"Saved configuration to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        return False

def check_local_mcp(config: Dict[str, Any]) -> bool:
    """Check if local MCP server is running."""
    try:
        response = requests.get(f"{config['local_mcp_url']}/health", timeout=5)
        if response.status_code == 200:
            logger.info("Local MCP server is running")
            return True
        else:
            logger.warning(f"Local MCP server returned status code: {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"Local MCP server not available: {str(e)}")
        return False

def check_smithery_api(config: Dict[str, Any]) -> bool:
    """Check if Smithery API is accessible with the provided key."""
    if not config.get("smithery_api_key"):
        logger.error("Smithery API key not configured")
        return False
        
    try:
        headers = {
            "Authorization": f"Bearer {config['smithery_api_key']}",
            "Content-Type": "application/json"
        }
        response = requests.get(f"{config['smithery_api_url']}/status", 
                             headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info("Smithery API connection successful")
            return True
        else:
            logger.error(f"Smithery API returned status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Smithery API connection failed: {str(e)}")
        return False

def redact_with_local_mcp(text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Redact text using local MCP server."""
    try:
        response = requests.post(
            f"{config['local_mcp_url']}/redact_text",
            json={"text": text},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Local redaction successful, found {len(result.get('matches', []))} matches")
            return result
        else:
            logger.error(f"Local redaction failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {"error": f"Redaction failed: {response.status_code}", "redacted_text": text}
    except Exception as e:
        logger.error(f"Local redaction error: {str(e)}")
        return {"error": str(e), "redacted_text": text}

def redact_with_smithery(text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Redact text using Smithery AI API."""
    if not config.get("smithery_api_key"):
        logger.error("Smithery API key not configured")
        return {"error": "Smithery API key not configured", "redacted_text": text}
        
    try:
        headers = {
            "Authorization": f"Bearer {config['smithery_api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "redaction_mode": "token",  # or "placeholder" depending on preference
            "detection_types": ["PII", "SENSITIVE"],  # customize as needed
            "return_matches": True
        }
        
        response = requests.post(
            f"{config['smithery_api_url']}/redact",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Smithery redaction successful, found {len(result.get('matches', []))} matches")
            return {
                "redacted_text": result.get("redacted_text", text),
                "matches": result.get("matches", [])
            }
        else:
            logger.error(f"Smithery redaction failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {"error": f"Smithery redaction failed: {response.status_code}", "redacted_text": text}
    except Exception as e:
        logger.error(f"Smithery redaction error: {str(e)}")
        return {"error": str(e), "redacted_text": text}

def redact_text(text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Redact text using the best available method based on configuration."""
    # Try Smithery first if API key is configured
    if config.get("smithery_api_key"):
        try:
            result = redact_with_smithery(text, config)
            if "error" not in result:
                return result
            else:
                logger.warning("Smithery redaction failed, falling back to local MCP")
        except Exception as e:
            logger.warning(f"Smithery redaction error, falling back to local MCP: {str(e)}")
    
    # Fall back to local MCP if configured or if Smithery failed
    if config.get("use_local_fallback", True):
        if check_local_mcp(config):
            return redact_with_local_mcp(text, config)
    
    # If all else fails, return original text
    logger.error("All redaction methods failed")
    return {"error": "All redaction methods failed", "redacted_text": text}

def configure_smithery():
    """Interactive configuration for Smithery API."""
    config = load_config()
    
    print("\n==== Smithery AI Integration Configuration ====\n")
    
    # Get API key
    if config.get("smithery_api_key"):
        masked_key = config["smithery_api_key"][:4] + "****" + config["smithery_api_key"][-4:]
        print(f"Current API key: {masked_key}")
        change = input("Change API key? (y/n): ").lower().strip()
        if change == 'y':
            config["smithery_api_key"] = input("Enter Smithery API key: ").strip()
    else:
        config["smithery_api_key"] = input("Enter Smithery API key: ").strip()
    
    # Configure API URL
    print(f"\nCurrent Smithery API URL: {config.get('smithery_api_url')}")
    change = input("Change API URL? (y/n): ").lower().strip()
    if change == 'y':
        config["smithery_api_url"] = input("Enter Smithery API URL: ").strip()
    
    # Configure local fallback
    print(f"\nCurrent local fallback setting: {config.get('use_local_fallback', True)}")
    change = input("Change local fallback setting? (y/n): ").lower().strip()
    if change == 'y':
        fallback = input("Use local fallback if Smithery fails? (y/n): ").lower().strip()
        config["use_local_fallback"] = (fallback == 'y')
    
    # Configure local MCP URL
    print(f"\nCurrent local MCP URL: {config.get('local_mcp_url')}")
    change = input("Change local MCP URL? (y/n): ").lower().strip()
    if change == 'y':
        config["local_mcp_url"] = input("Enter local MCP URL: ").strip()
    
    # Test configurations
    print("\nTesting configurations...")
    
    # Test Smithery API
    if config.get("smithery_api_key"):
        if check_smithery_api(config):
            print("✅ Smithery API connection successful")
        else:
            print("❌ Smithery API connection failed")
    else:
        print("⚠️ Smithery API key not configured")
    
    # Test local MCP
    if check_local_mcp(config):
        print("✅ Local MCP server is running")
    else:
        print("❌ Local MCP server not available")
    
    # Save configuration
    save = input("\nSave configuration? (y/n): ").lower().strip()
    if save == 'y':
        if save_config(config):
            print("✅ Configuration saved")
        else:
            print("❌ Failed to save configuration")
    
    return config

def main():
    """Main function to handle command-line interface."""
    parser = argparse.ArgumentParser(description="Smithery AI Integration for MCP Redaction")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Configure command
    configure_parser = subparsers.add_parser("configure", help="Configure Smithery integration")
    
    # Redact command
    redact_parser = subparsers.add_parser("redact", help="Redact text")
    redact_parser.add_argument("--text", help="Text to redact")
    redact_parser.add_argument("--file", help="File containing text to redact")
    redact_parser.add_argument("--output", help="Output file for redacted text")
    
    # Claude integration command
    claude_parser = subparsers.add_parser("claude", help="Send redacted text to Claude")
    claude_parser.add_argument("--text", help="Text to redact and send to Claude")
    claude_parser.add_argument("--file", help="File containing text to redact and send to Claude")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Execute command
    if args.command == "configure":
        configure_smithery()
    elif args.command == "redact":
        # Get text to redact
        text = ""
        if args.text:
            text = args.text
        elif args.file:
            try:
                with open(args.file, 'r') as f:
                    text = f.read()
            except Exception as e:
                print(f"Error reading file: {str(e)}")
                return
        else:
            print("Reading from stdin...")
            text = sys.stdin.read()
        
        # Redact text
        result = redact_text(text, config)
        
        # Output redacted text
        if args.output:
            try:
                with open(args.output, 'w') as f:
                    f.write(result["redacted_text"])
                print(f"Redacted text written to {args.output}")
            except Exception as e:
                print(f"Error writing to file: {str(e)}")
                print(result["redacted_text"])
        else:
            print(result["redacted_text"])
    elif args.command == "claude":
        # Get text to redact
        text = ""
        if args.text:
            text = args.text
        elif args.file:
            try:
                with open(args.file, 'r') as f:
                    text = f.read()
            except Exception as e:
                print(f"Error reading file: {str(e)}")
                return
        else:
            print("Reading from stdin...")
            text = sys.stdin.read()
        
        # Redact text
        result = redact_text(text, config)
        
        # Build command to send to Claude
        try:
            import subprocess
            print("Sending redacted text to Claude...")
            claude_cmd = ["claude", "--print", result["redacted_text"]]
            subprocess.run(claude_cmd)
        except Exception as e:
            print(f"Error sending to Claude: {str(e)}")
            print("Redacted text:")
            print(result["redacted_text"])
    else:
        parser.print_help()

if __name__ == "__main__":
    main()