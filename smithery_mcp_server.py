#!/usr/bin/env python3
"""
Ultra-minimalist MCP server for Smithery deployments.
This server implements just enough functionality to pass Smithery's tool scanning
without any dependencies on the full MCP implementation.
"""
import os
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# Define the tools we want to expose
TOOLS = [
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

# Basic regex patterns for redaction
PATTERNS = {
    "SSN": (r"\b\d{3}-\d{2}-\d{4}\b", "<SSN>"),
    "Email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "<EMAIL>"),
    "CreditCard": (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "<CREDIT_CARD>")
}

class MCPHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for MCP requests"""
    
    def do_GET(self):
        """Handle GET requests - primarily for Smithery's healthcheck and tool discovery"""
        # Health check endpoint
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "ok", "version": "1.0.0"}
            self.wfile.write(json.dumps(response).encode())
            
        # Root endpoint
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "name": "Rules Engine MCP (Smithery Version)",
                "version": "1.0.0",
                "status": "active",
                "endpoints": ["/redact_text", "/mcp", "/health"]
            }
            self.wfile.write(json.dumps(response).encode())
            
        # MCP endpoint - for tool discovery
        elif self.path == "/mcp":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"methods": TOOLS}
            }
            self.wfile.write(json.dumps(response).encode())
            
        # Default 404 for other paths
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())
            
    def do_HEAD(self):
        """Handle HEAD requests for healthchecks"""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
    def do_POST(self):
        """Handle POST requests for MCP tools"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
            self.wfile.write(json.dumps(response).encode())
            return
            
        # Handle MCP endpoint
        if self.path == "/mcp":
            # Get the request ID
            request_id = data.get("id", 1)
            
            # Handle tool discovery
            if data.get("method") == "rpc.discover" or data.get("method") == "tools/list":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"methods": TOOLS}
                }
                self.wfile.write(json.dumps(response).encode())
                return
                
            # Handle execute method for redact_text
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
                
                # Implement redact_text tool
                if tool_name == "redact_text":
                    text = parameters.get("text", "")
                    if not text:
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params: text parameter is required"
                            }
                        }
                        self.wfile.write(json.dumps(response).encode())
                        return
                    
                    # Process the text with our patterns
                    redacted = text
                    matches = []
                    
                    # Apply each pattern
                    import re
                    for pattern_name, (pattern, replacement) in PATTERNS.items():
                        # Find matches
                        pattern_matches = re.findall(pattern, redacted)
                        for match in pattern_matches:
                            matches.append({
                                "original": match,
                                "replacement": replacement,
                                "rule_name": pattern_name
                            })
                        # Apply redaction
                        redacted = re.sub(pattern, replacement, redacted)
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "redacted_text": redacted,
                            "matches": matches
                        }
                    }
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Implement process_text - simplified version that just calls redact_text
                elif tool_name == "process_text":
                    text = parameters.get("text", "")
                    if not text:
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params: text parameter is required"
                            }
                        }
                        self.wfile.write(json.dumps(response).encode())
                        return
                    
                    # Process the text with our patterns (same as redact_text)
                    redacted = text
                    results = []
                    
                    # Apply each pattern
                    import re
                    for pattern_name, (pattern, replacement) in PATTERNS.items():
                        # Find matches
                        pattern_matches = re.findall(pattern, redacted)
                        for match in pattern_matches:
                            results.append({
                                "rule_id": f"{pattern_name.lower()}-rule",
                                "rule_name": pattern_name,
                                "action": "redact",
                                "original": match,
                                "replacement": replacement
                            })
                        # Apply redaction
                        redacted = re.sub(pattern, replacement, redacted)
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "processed_text": redacted,
                            "results": results,
                            "status": "success"
                        }
                    }
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Unknown tool
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    }
                }
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Unknown method
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {data.get('method')}"
                }
            }
            self.wfile.write(json.dumps(response).encode())
            return
            
        # Handle direct redact_text endpoint
        elif self.path == "/redact_text":
            try:
                text = data.get("text", "")
                if not text:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    response = {"error": "text parameter is required"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Process the text with our patterns
                redacted = text
                matches = []
                
                # Apply each pattern
                import re
                for pattern_name, (pattern, replacement) in PATTERNS.items():
                    # Find matches
                    pattern_matches = re.findall(pattern, redacted)
                    for match in pattern_matches:
                        matches.append({
                            "original": match,
                            "replacement": replacement,
                            "rule_name": pattern_name
                        })
                    # Apply redaction
                    redacted = re.sub(pattern, replacement, redacted)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {
                    "redacted_text": redacted,
                    "matches": matches
                }
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
        
        # Default 404 for other paths
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

def main():
    """Run the server"""
    port = int(os.environ.get('PORT', 6366))
    server_address = ('', port)
    
    print(f"Starting Smithery-compatible MCP server on port {port}")
    httpd = HTTPServer(server_address, MCPHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()