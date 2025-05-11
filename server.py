#!/usr/bin/env python3
import os
import sys
import logging
import subprocess
import json
import uvicorn
from fastapi import FastAPI, Request, Response
from typing import Dict, Any, Optional, List

# Create an application
app = FastAPI()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmitheryMCP")

# Define default tools
DEFAULT_TOOLS = [
    {
        "name": "redact_text",
        "description": "Redacts sensitive information from text based on configured patterns.",
        "parameters": {
            "text": {
                "type": "string",
                "description": "The text to redact"
            }
        }
    },
    {
        "name": "process_text",
        "description": "Processes text through rules engine with options for rule sets.",
        "parameters": {
            "text": {
                "type": "string",
                "description": "The text to process"
            },
            "rule_sets": {
                "type": "array",
                "description": "Optional IDs of rule sets to apply",
                "items": {
                    "type": "string"
                }
            }
        }
    }
]

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MCP Rules Engine",
        "version": "1.0.0",
        "status": "active",
        "endpoints": ["/redact_text", "/process_text", "/mcp", "/health"]
    }

@app.get("/mcp-tools")
async def get_tools():
    """Lazy-loaded tools endpoint."""
    logger.info("Tools list requested at /mcp-tools")
    return {"tools": DEFAULT_TOOLS}

@app.get("/mcp")
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP endpoint that forwards to the actual MCP server."""
    try:
        # Get request data
        if request.method == "POST":
            data = await request.json()
            logger.info(f"MCP request received: {data.get('method', 'unknown_method')}")

            # Check if it's a tool discovery request
            if data.get("method") == "rpc.discover" or data.get("method") == "tools/list":
                logger.info("Tool discovery request received, sending tool list")
                return {
                    "jsonrpc": "2.0",
                    "id": data.get("id"),
                    "result": {"methods": DEFAULT_TOOLS}
                }

            # For actual tool calls, forward to the MCP implementation
            # In this lazy-loading version, we just handle 'redact_text' directly
            if data.get("method") == "execute" or data.get("method") == "tools/call":
                tool_name = data.get("params", {}).get("name", "")
                parameters = data.get("params", {}).get("parameters", {})

                if tool_name == "redact_text":
                    # Simple implementation for lazy loading
                    text = parameters.get("text", "")
                    import re
                    # Basic SSN redaction as an example
                    redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "<SSN>", text)
                    # Basic email redaction
                    redacted = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "<EMAIL>", redacted)
                    # Credit card redaction
                    redacted = re.sub(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "<CREDIT_CARD>", redacted)

                    return {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "result": {
                            "redacted_text": redacted,
                            "matches": [{"original": m, "replacement": "<REDACTED>", "rule_name": "Rule"}
                                       for m in re.findall(r"\b\d{3}-\d{2}-\d{4}\b", text)]
                        }
                    }

        # GET requests or unhandled methods just return the tool list
        return {"jsonrpc": "2.0", "id": None, "result": {"methods": DEFAULT_TOOLS}}

    except Exception as e:
        logger.error(f"Error handling MCP request: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": None if "data" not in locals() else data.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal server error: {str(e)}"
            }
        }

def start_mcp_server():
    """Start the actual MCP server in the background."""
    logger.info("Starting MCP Rules Engine server in the background")
    
    # Path to the actual MCP server script
    script_path = "app/rules_engine_mcp_sse.py"
    
    # Make sure the script exists
    if not os.path.exists(script_path):
        logger.error(f"MCP server script not found: {script_path}")
        sys.exit(1)
    
    # Start the MCP server in the background
    try:
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"MCP server started with PID {process.pid}")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        sys.exit(1)

def main():
    """Entry point for Smithery deployment."""
    logger.info("Starting lazy-loading proxy server for Smithery")
    
    # Start the actual MCP server in the background
    # start_mcp_server()
    
    # Start the proxy server
    uvicorn.run(app, host="0.0.0.0", port=6366)

if __name__ == "__main__":
    main()