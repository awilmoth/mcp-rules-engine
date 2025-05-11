#!/usr/bin/env python3
import http.server
import json
import re
import socket
import logging
import sys
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SimpleMCPServer')

# Port to use
PORT = 6371

# Define sensitive data patterns to redact
PATTERNS = [
    {"name": "SSN", "pattern": r"\b\d{3}-\d{2}-\d{4}\b", "replacement": "<SSN>"},
    {"name": "Email", "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "replacement": "<EMAIL>"},
    {"name": "CreditCard", "pattern": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "replacement": "<CREDIT_CARD>"},
    {"name": "Phone", "pattern": r"\b\d{3}-\d{3}-\d{4}\b", "replacement": "<PHONE>"}
]

# Default MCP tools
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

class MCPRequestHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self._set_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        logger.info(f"GET request to {path}")
        
        if path == "/health" or path == "/healthcheck":
            # Health check endpoint
            self._set_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            
        elif path == "/mcp" or path == "/":
            # Tool discovery for GET requests
            response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"methods": DEFAULT_TOOLS}
            }
            self._set_headers()
            self.wfile.write(json.dumps(response).encode())
            
        else:
            # Not found
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Parse JSON request
        try:
            data = json.loads(post_data)
            method = data.get('method', '')
            params = data.get('params', {})
            request_id = data.get('id', 1)
            
            logger.info(f"POST request to {self.path}, method: {method}")
            
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
                            "name": "Simple MCP Redaction Server",
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
                    "result": {"tools": DEFAULT_TOOLS}
                }
                if method == "rpc.discover":
                    response["result"] = {"methods": DEFAULT_TOOLS}
                
            elif method == "ping":
                # Ping response
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {}
                }
                
            elif method == "tools/call":
                # Tool call
                tool_name = params.get('name', '')
                tool_params = params.get('arguments', params.get('input', {}))
                
                if tool_name == "redact_text":
                    text = tool_params.get('text', '')
                    result = self.redact_text(text)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                    
                elif tool_name == "process_text":
                    text = tool_params.get('text', '')
                    result = self.process_text(text)
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
            
            # Send response
            self._set_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except json.JSONDecodeError:
            # Invalid JSON
            self._set_headers(400)
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
            self._set_headers(500)
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            self.wfile.write(json.dumps(response).encode())
    
    def redact_text(self, text):
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
    
    def process_text(self, text, rule_sets=None):
        """Process text with rule engine details."""
        redaction_result = self.redact_text(text)
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

def run_server():
    try:
        server_address = ('0.0.0.0', PORT)
        httpd = http.server.HTTPServer(server_address, MCPRequestHandler)
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        
        print(f"Starting Simple MCP Server on http://{host_ip}:{PORT}")
        print(f"MCP endpoint: http://{host_ip}:{PORT}/mcp")
        print(f"Health check: http://{host_ip}:{PORT}/health")
        print("Press Ctrl+C to stop the server")
        
        # Log server start
        logger.info(f"Server started on http://0.0.0.0:{PORT}")
        
        # Start the server
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\nServer stopped")
        httpd.server_close()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()