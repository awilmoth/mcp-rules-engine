#!/usr/bin/env python3
"""
Simple MCP server that supports STDIO transport for Smithery deployments.
"""
import sys
import json
import re
import logging
import argparse
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/mcp_stdio.log'
)
logger = logging.getLogger('SimpleMCPStdio')

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

def redact_text(text):
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

def process_text(text, rule_sets=None):
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

def handle_jsonrpc_request(request_data):
    """Process a JSON-RPC request and return a response."""
    try:
        # Parse the request
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
            
        elif method in ["tools/call", "execute"]:
            # Tool call
            tool_name = ""
            tool_params = {}
            
            if method == "execute":
                tool_name = params.get("name", "")
                tool_params = params.get("parameters", {})
            else:  # tools/call
                tool_name = params.get("name", "")
                tool_params = params.get("arguments", {})
            
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
                rule_sets = tool_params.get("rule_sets", None)
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
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        # Server error
        return {
            "jsonrpc": "2.0",
            "id": request_id if 'request_id' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

def read_stdin_thread(stdin_queue):
    """Thread to read from stdin."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                logger.info("End of input stream, terminating reader thread")
                break
            stdin_queue.put(line)
        except Exception as e:
            logger.error(f"Error reading from stdin: {str(e)}")
            break

def run_stdio_server():
    """Run the server in STDIO mode for Smithery."""
    logger.info("Starting MCP server in STDIO mode")
    
    stdin_queue = queue.Queue()
    
    # Start the thread to read from stdin
    reader_thread = threading.Thread(target=read_stdin_thread, args=(stdin_queue,))
    reader_thread.daemon = True
    reader_thread.start()
    
    # Process JSON-RPC requests from stdin
    try:
        buffer = ""
        while True:
            try:
                line = stdin_queue.get(timeout=0.1)
                
                # Add the line to our buffer
                buffer += line
                
                # Try to parse it as JSON
                try:
                    request = json.loads(buffer)
                    
                    # Successfully parsed, process the request
                    response = handle_jsonrpc_request(request)
                    
                    # Send the response to stdout
                    json_response = json.dumps(response)
                    logger.info(f"Sending response: {json_response[:100]}...")
                    sys.stdout.write(json_response + "\n")
                    sys.stdout.flush()
                    
                    # Clear the buffer for the next request
                    buffer = ""
                    
                except json.JSONDecodeError:
                    # Not a complete JSON object yet, keep reading
                    pass
                    
            except queue.Empty:
                # No data available, just continue
                pass
                
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

def run_http_server(host="0.0.0.0", port=6366):
    """Run the server in HTTP mode."""
    import http.server
    import socket
    
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
            import urllib.parse
            parsed_path = urllib.parse.urlparse(self.path)
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
                
                # Process the request
                response = handle_jsonrpc_request(data)
                
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
    
    try:
        server_address = (host, port)
        httpd = http.server.HTTPServer(server_address, MCPRequestHandler)
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        
        print(f"Starting Simple MCP Server on http://{host_ip}:{port}")
        print(f"MCP endpoint: http://{host_ip}:{port}/mcp")
        print(f"Health check: http://{host_ip}:{port}/health")
        print("Press Ctrl+C to stop the server")
        
        # Log server start
        logger.info(f"Server started on http://{host}:{port}")
        
        # Start the server
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\nServer stopped")
        httpd.server_close()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Simple MCP Server with STDIO or HTTP transport.')
    parser.add_argument('--stdio', action='store_true', help='Run in STDIO mode for Smithery')
    parser.add_argument('--host', default='0.0.0.0', help='Host for HTTP mode')
    parser.add_argument('--port', type=int, default=6366, help='Port for HTTP mode')
    
    args = parser.parse_args()
    
    if args.stdio:
        run_stdio_server()
    else:
        run_http_server(args.host, args.port)

if __name__ == "__main__":
    main()