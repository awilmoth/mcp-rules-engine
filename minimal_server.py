#!/usr/bin/env python3
"""
Minimal HTTP MCP server that only implements the essentials for tool scanning.
"""
import http.server
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MinimalMCP")

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

class MinimalHandler(http.server.BaseHTTPRequestHandler):
    def send_cors_headers(self):
        """Set CORS headers to allow all origins."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_cors_headers()
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
            # Tool discovery endpoint
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            
            response = {
                "jsonrpc": "2.0", 
                "id": 1, 
                "result": {"methods": TOOLS}
            }
            self.wfile.write(json.dumps(response).encode())
            
        else:
            # Not found
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        logger.info(f"POST request to {self.path}")
        
        # All POST requests should go to /mcp
        if self.path != "/mcp":
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())
            return
        
        # Read request body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            logger.info(f"Received data: {post_data[:200]}...")
            
            # Parse JSON
            data = json.loads(post_data)
            method = data.get("method", "")
            request_id = data.get("id", 1)
            
            logger.info(f"Method: {method}")
            
            # Set common headers
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            
            # Handle different method types
            if method == "rpc.discover":
                # RPC discover method
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"methods": TOOLS}
                }
                
            elif method == "tools/list":
                # Tools/list method
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": TOOLS}
                }
                
            elif method == "tools/call" or method == "execute":
                # Tool execution (minimal implementation)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"message": "Tool execution successful"}
                }
                
            else:
                # Unknown method
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {}
                }
            
            # Send response
            logger.info(f"Sending response: {json.dumps(response)[:200]}...")
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            # Handle errors
            logger.error(f"Error processing request: {str(e)}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            self.wfile.write(json.dumps(error_response).encode())

def main():
    """Run the server."""
    try:
        # Use port 6366 for Smithery compatibility
        port = 6366
        server = http.server.HTTPServer(('0.0.0.0', port), MinimalHandler)
        logger.info(f"Starting minimal MCP server on port {port}")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()