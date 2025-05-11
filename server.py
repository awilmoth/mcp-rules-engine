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
@app.head("/health")
async def health_check():
    """Health check endpoint that supports HEAD and GET requests."""
    return {"status": "ok", "version": "1.0.0", "tools_available": True}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MCP Rules Engine",
        "version": "1.0.0",
        "status": "active",
        "endpoints": ["/redact_text", "/process_text", "/mcp", "/health", "/debug"]
    }

@app.get("/debug")
async def debug_info():
    """Debug endpoint for Smithery."""
    import platform
    import sys
    import os

    return {
        "status": "ok",
        "version": "1.0.0",
        "python": sys.version,
        "platform": platform.platform(),
        "environment": {
            key: value for key, value in os.environ.items()
            if "key" not in key.lower() and "secret" not in key.lower() and "token" not in key.lower()
        },
        "tools": DEFAULT_TOOLS,
        "note": "This server implements MCP protocol with JSON-RPC over HTTP and supports tool discovery without authentication."
    }

@app.get("/mcp-tools")
async def get_tools():
    """Lazy-loaded tools endpoint."""
    logger.info("Tools list requested at /mcp-tools")
    return {"tools": DEFAULT_TOOLS}

@app.get("/mcp", response_model=None)
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP endpoint that forwards to the actual MCP server."""
    try:
        # First, handle GET requests - they always return the tool list for Smithery tool scanning
        if request.method == "GET":
            logger.info("GET request to /mcp - returning tool list for Smithery")
            return {
                "jsonrpc": "2.0", 
                "id": 1, 
                "result": {"methods": DEFAULT_TOOLS}
            }
            
        # For POST requests, parse the JSON data
        if request.method == "POST":
            try:
                data = await request.json()
            except Exception as json_error:
                logger.error(f"Error parsing JSON request: {str(json_error)}")
                return {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error: Invalid JSON"
                    }
                }
            
            logger.info(f"MCP request received: {data.get('method', 'unknown_method')}")
            request_id = data.get("id", 1)  # Default ID if none provided
            
            # Always support tool discovery requests without authentication
            # This is crucial for Smithery scanning
            if data.get("method") == "rpc.discover" or data.get("method") == "tools/list":
                logger.info("Tool discovery request received, sending tool list")
                return {
                    "jsonrpc": "2.0", 
                    "id": request_id, 
                    "result": {"methods": DEFAULT_TOOLS}
                }
                
            # For actual tool calls, implement lazy loading
            if data.get("method") == "execute" or data.get("method") == "tools/call":
                # Parse parameters
                tool_name = ""
                parameters = {}
                
                if data.get("method") == "execute":
                    params = data.get("params", {})
                    tool_name = params.get("name", "")
                    parameters = params.get("parameters", {})
                else:  # tools/call
                    tool_name = data.get("params", {}).get("name", "")
                    parameters = data.get("params", {}).get("parameters", {})
                
                # Implement redact_text tool directly
                if tool_name == "redact_text":
                    text = parameters.get("text", "")
                    if not text:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params: text parameter is required"
                            }
                        }
                    
                    import re
                    # Basic redaction implementation
                    redacted = text
                    matches = []
                    
                    # SSN redaction
                    ssn_matches = re.findall(r"\b\d{3}-\d{2}-\d{4}\b", text)
                    for match in ssn_matches:
                        matches.append({
                            "original": match,
                            "replacement": "<SSN>",
                            "rule_name": "SSN"
                        })
                    redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "<SSN>", redacted)
                    
                    # Email redaction
                    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                    email_matches = re.findall(email_pattern, redacted)
                    for match in email_matches:
                        matches.append({
                            "original": match,
                            "replacement": "<EMAIL>",
                            "rule_name": "Email"
                        })
                    redacted = re.sub(email_pattern, "<EMAIL>", redacted)
                    
                    # Credit card redaction
                    cc_pattern = r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"
                    cc_matches = re.findall(cc_pattern, redacted)
                    for match in cc_matches:
                        matches.append({
                            "original": match,
                            "replacement": "<CREDIT_CARD>",
                            "rule_name": "CreditCard"
                        })
                    redacted = re.sub(cc_pattern, "<CREDIT_CARD>", redacted)
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "redacted_text": redacted,
                            "matches": matches
                        }
                    }
                
                # Implement process_text tool directly
                elif tool_name == "process_text":
                    text = parameters.get("text", "")
                    if not text:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params: text parameter is required"
                            }
                        }
                    
                    # Simple implementation that just forwards to redact_text
                    import re
                    redacted = text
                    results = []
                    
                    # SSN redaction
                    ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
                    ssn_matches = re.findall(ssn_pattern, redacted)
                    for match in ssn_matches:
                        results.append({
                            "rule_id": "ssn-rule",
                            "rule_name": "SSN",
                            "action": "redact",
                            "original": match,
                            "replacement": "<SSN>"
                        })
                    redacted = re.sub(ssn_pattern, "<SSN>", redacted)
                    
                    # Email redaction
                    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                    email_matches = re.findall(email_pattern, redacted)
                    for match in email_matches:
                        results.append({
                            "rule_id": "email-rule",
                            "rule_name": "Email",
                            "action": "redact",
                            "original": match,
                            "replacement": "<EMAIL>"
                        })
                    redacted = re.sub(email_pattern, "<EMAIL>", redacted)
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "processed_text": redacted,
                            "results": results,
                            "status": "success"
                        }
                    }
                
                # Unknown tool
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {tool_name}"
                        }
                    }
            
            # Unknown method
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {data.get('method')}"
                }
            }
        
        # Fallback response for all other cases
        return {
            "jsonrpc": "2.0", 
            "id": 1, 
            "result": {"methods": DEFAULT_TOOLS}
        }
        
    except Exception as e:
        logger.error(f"Error handling MCP request: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": 1,  # Use default ID
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