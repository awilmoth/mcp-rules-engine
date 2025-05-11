#!/usr/bin/env python3
import http.server
import json
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmitheryScan")

# Default MCP tools for scanning
DEFAULT_TOOLS = [
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

class ScanHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for Smithery scanning."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(format % args)
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        logger.info(f"GET request to {self.path}")
        
        if self.path == "/health" or self.path == "/healthcheck":
            # Health check endpoint
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            
        elif self.path == "/mcp" or self.path == "/":
            # Simple scanning response - just return the tool list
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            response = {
                "jsonrpc": "2.0", 
                "id": 1, 
                "result": {"methods": DEFAULT_TOOLS}
            }
            self.wfile.write(json.dumps(response).encode())
            
        else:
            # Not found
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Not found: {self.path}".encode())
    
    def do_POST(self):
        """Handle POST requests."""
        logger.info(f"POST request to {self.path}")
        
        if self.path != "/mcp":
            # Not found
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Not found: {self.path}".encode())
            return
        
        # Read request data
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode()
        
        try:
            # Parse JSON request
            data = json.loads(post_data)
            method = data.get("method", "")
            request_id = data.get("id", 1)
            logger.info(f"MCP method: {method}")
            
            # For scanning, just return tool list for any method
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            if method in ["rpc.discover", "tools/list"]:
                # Tool discovery methods
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"methods": DEFAULT_TOOLS}
                }
                if method == "tools/list":
                    response["result"] = {"tools": DEFAULT_TOOLS}
            else:
                # For any other method, return success but empty result
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {}
                }
            
            self.wfile.write(json.dumps(response).encode())
            
        except json.JSONDecodeError:
            # Invalid JSON
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                }
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            # Server error
            logger.error(f"Error processing request: {str(e)}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            self.wfile.write(json.dumps(response).encode())

def main():
    """Start the Smithery scan server."""
    try:
        port = 6366
        server = http.server.HTTPServer(("0.0.0.0", port), ScanHandler)
        logger.info(f"Starting Smithery scan server on port {port}")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        server.server_close()
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
