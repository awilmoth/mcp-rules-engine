#!/usr/bin/env python3
import os
import sys
import logging
import subprocess

def main():
    """Simple entry point for Smithery deployment."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("SmitheryMCP")
    
    # Log startup
    logger.info("Starting MCP Rules Engine server via Smithery")
    
    # Path to the actual MCP server script
    script_path = "app/rules_engine_mcp_sse.py"
    
    # Make sure the script exists
    if not os.path.exists(script_path):
        logger.error(f"MCP server script not found: {script_path}")
        sys.exit(1)
    
    # Start the MCP server
    logger.info(f"Running: python {script_path}")
    
    try:
        # Run the MCP server script directly
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"MCP server failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down MCP server")
        sys.exit(0)

if __name__ == "__main__":
    main()