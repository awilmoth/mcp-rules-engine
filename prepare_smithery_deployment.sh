#!/bin/bash
# Script to prepare the MCP server for Smithery deployment

# Change to the project directory
cd "$(dirname "$0")"

# Make sure we have a virtual environment activated
if [ -z "$VIRTUAL_ENV" ]; then
  source venv-linux/bin/activate
fi

echo "Creating Smithery deployment configuration..."

# Create smithery.json configuration file
cat > smithery.json << EOF
{
  "name": "Rules Engine MCP",
  "description": "Regex-based sensitive information redaction MCP server",
  "version": "1.0.0",
  "transport": "http",
  "endpoint": "/mcp",
  "health_endpoint": "/health",
  "tools_endpoint": "/mcp-tools",
  "tools": [
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
  ],
  "requirements": [
    "fastapi",
    "uvicorn",
    "pydantic",
    "mcp"
  ],
  "config_schema": {
    "type": "object",
    "properties": {
      "default_ruleset": {
        "type": "string",
        "description": "Default ruleset to use"
      }
    }
  }
}
EOF

# Create a deployment package
echo "Creating deployment package..."

# Create directory for deployment files
mkdir -p smithery_deployment
cp app/rules_engine_mcp_sse.py smithery_deployment/
cp -r app/RulesEngineMCP smithery_deployment/

# Create README.md for Smithery
cat > smithery_deployment/README.md << EOF
# Rules Engine MCP Server

This MCP server provides regex-based redaction of sensitive information like:
- SSNs
- Credit card numbers
- Email addresses
- Phone numbers
- API keys and credentials

## Tools

### redact_text
Redacts sensitive information from the provided text.

### process_text
Processes text through the rules engine with options for specific rule sets.

## Deployment
This server is designed to run as a Smithery deployment using HTTP transport.
Persistent rules can be configured through the Smithery interface.
EOF

echo "Creating deployment script..."
cat > smithery_deployment/deploy.py << EOF
#!/usr/bin/env python3
"""
Smithery deployment script for MCP Rules Engine
"""
import os
import sys
import json
import logging
from pathlib import Path

# Ensure the rules_engine_mcp_sse.py is in the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the MCP server module
from rules_engine_mcp_sse import app as mcp_app, logger

if __name__ == "__main__":
    # Get port from environment variable (provided by Smithery)
    port = int(os.environ.get("PORT", 6366))
    
    # Get configuration from environment variable (if provided by Smithery)
    config = {}
    if "SMITHERY_CONFIG" in os.environ:
        try:
            config = json.loads(os.environ["SMITHERY_CONFIG"])
            logger.info(f"Loaded configuration from Smithery: {config}")
        except Exception as e:
            logger.error(f"Error loading Smithery configuration: {str(e)}")
    
    # Start the server
    logger.info(f"Starting Smithery deployment on port {port}")
    import uvicorn
    uvicorn.run(mcp_app, host="0.0.0.0", port=port)
EOF

# Create a ZIP package
echo "Creating ZIP package for upload to Smithery..."
cd smithery_deployment
zip -r ../rules_engine_mcp.zip .
cd ..

echo ""
echo "=== Smithery Deployment Preparation Complete ==="
echo ""
echo "You now have:"
echo "1. smithery.json - Configuration file for Smithery"
echo "2. rules_engine_mcp.zip - Deployment package ready to upload"
echo ""
echo "To deploy to Smithery:"
echo "1. Go to the Smithery website and create an account if needed"
echo "2. Navigate to Deployments and click 'Add Server'"
echo "3. Upload the ZIP package and follow the instructions"
echo ""
echo "Your MCP server will be hosted by Smithery and available via HTTP"
echo "This will allow seamless integration with Claude and other AI tools"