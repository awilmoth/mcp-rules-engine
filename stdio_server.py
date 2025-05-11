#!/usr/bin/env python3
"""
STDIO-based MCP server that reads JSON-RPC requests from stdin and writes responses to stdout.
This is designed for direct integration with Smithery using the STDIO transport.
"""
import sys
import json
import logging
import re
from typing import Dict, Any, List, Optional

# Configure logging to a file since we can't write to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/stdio_server.log'
)
logger = logging.getLogger("STDIOServer")

# Define tools with inputSchema format
TOOLS = [
    {
        "name": "redact_text",
        "description": "Redacts sensitive information from text based on configured patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to redact"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "process_text",
        "description": "Processes text through rules engine with options for rule sets.",
        "inputSchema": {
            "type": "object",
            "properties": {
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
            },
            "required": ["text"]
        }
    }
]

# Define redaction patterns
PATTERNS = [
    {"name": "SSN", "pattern": r"\b\d{3}-\d{2}-\d{4}\b", "replacement": "<SSN>"},
    {"name": "Email", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "replacement": "<EMAIL>"},
    {"name": "CreditCard", "pattern": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "replacement": "<CREDIT_CARD>"},
    {"name": "Phone", "pattern": r"\b\d{3}-\d{3}-\d{4}\b", "replacement": "<PHONE>"}
]

def redact_text(text: str) -> Dict[str, Any]:
    """Redact sensitive information from text."""
    if not text:
        return {"redacted_text": "", "matches": []}
    
    redacted = text
    matches = []
    
    # Apply each pattern
    for pattern_info in PATTERNS:
        pattern = re.compile(pattern_info["pattern"])
        matches_found = pattern.findall(redacted)
        
        for match in matches_found:
            matches.append({
                "original": match,
                "replacement": pattern_info["replacement"],
                "rule_name": pattern_info["name"]
            })
        
        redacted = pattern.sub(pattern_info["replacement"], redacted)
    
    return {"redacted_text": redacted, "matches": matches}

def process_text(text: str, rule_sets: Optional[List[str]] = None) -> Dict[str, Any]:
    """Process text with rule engine details."""
    redaction_result = redact_text(text)
    processed_text = redaction_result["redacted_text"]
    
    results = []
    for match in redaction_result["matches"]:
        results.append({
            "rule_id": match["rule_name"].lower(),
            "rule_name": match["rule_name"],
            "action": "redact",
            "original": match["original"],
            "replacement": match["replacement"]
        })
    
    return {
        "processed_text": processed_text,
        "results": results,
        "status": "success"
    }

def handle_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a JSON-RPC request and return a response."""
    method = request_data.get('method', '')
    params = request_data.get('params', {})
    request_id = request_data.get('id', 1)
    
    logger.info(f"Received request with method: {method}")
    
    # Handle various MCP methods
    if method == "initialize":
        # Initialization
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "capabilities": {
                    "tools": {"supports": True}
                },
                "serverInfo": {
                    "name": "MCP STDIO Server",
                    "version": "1.0.0"
                },
                "protocolVersion": "2024-11-05"
            }
        }
        
    elif method in ["rpc.discover", "tools/list"]:
        # Tool discovery
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS}
        }
        if method == "rpc.discover":
            response["result"] = {"methods": TOOLS}
        
    elif method == "ping":
        # Ping response
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }
        
    elif method in ["tools/call", "execute"]:
        # Tool execution
        tool_name = ""
        tool_params = {}
        
        if method == "execute":
            # Legacy format
            tool_name = params.get("name", "")
            tool_params = params.get("parameters", {})
        else:  # tools/call
            # New format
            tool_name = params.get("name", "")
            tool_params = params.get("arguments", params.get("parameters", {}))
        
        if tool_name == "redact_text":
            text = tool_params.get("text", "")
            result = redact_text(text)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        elif tool_name == "process_text":
            text = tool_params.get("text", "")
            rule_sets = tool_params.get("rule_sets")
            result = process_text(text, rule_sets)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        else:
            # Unknown tool
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {tool_name}"
                }
            }
    
    else:
        # Unknown method
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }
    
    return response

def main():
    """Run the STDIO server."""
    logger.info("Starting MCP server with STDIO transport")
    
    # Process JSON-RPC requests from stdin
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            logger.info(f"Received line: {line[:100]}...")
            
            try:
                # Parse the JSON request
                request = json.loads(line)
                
                # Handle the request
                response = handle_request(request)
                
                # Write the response to stdout
                json_response = json.dumps(response)
                logger.info(f"Sending response: {json_response[:100]}...")
                print(json_response, flush=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON: {str(e)}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error: Invalid JSON"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()