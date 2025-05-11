# Linux Setup for Claude Code Integration

This guide will help you set up the Rules Engine MCP server to work with Claude Code on Linux.

## Prerequisites

- Python 3.8 or later installed
- Claude Code installed
- Virtual environment setup (recommended)

## Installation Steps

1. **Clone or extract the repository**
   
   Make sure the repository is extracted to `/home/YOUR_USERNAME/mcp-redacted` or modify the paths in the configuration files accordingly.

2. **Set up a Python virtual environment**
   
   Open a terminal and run:
   ```bash
   cd ~/mcp-redacted
   python -m venv venv-linux
   source venv-linux/bin/activate
   pip install -r requirements.txt
   ```

3. **Test the Rules Engine MCP Server**
   
   Start the MCP server manually:
   ```bash
   source venv-linux/bin/activate
   python app/rules_engine_mcp.py
   ```
   
   Open another terminal and run the test client:
   ```bash
   source venv-linux/bin/activate
   python improved_mcp_client.py
   ```
   
   If the test client successfully connects and can interact with the server, the setup is working.

4. **Configure Claude CLI**

   Use the provided startup script to launch Claude with the MCP configuration:
   ```bash
   chmod +x start-claude-code.sh
   ./start-claude-code.sh
   ```

   This script:
   - Checks if the MCP server is running and starts it if needed
   - Searches for either `claude` or `claude-code` executables in common installation paths
   - If not found, prompts for the path to the Claude executable
   - Launches Claude with the proper MCP configuration

   If Claude isn't found, the script will still start the MCP server and provide instructions for manually running Claude with the configuration.

5. **Create a Desktop Shortcut** (optional)

   Create a .desktop file for easy launching:
   ```bash
   cat > ~/.local/share/applications/claude-mcp.desktop << EOF
   [Desktop Entry]
   Name=Claude with MCP
   Comment=Launch Claude with Rules Engine MCP
   Exec=/home/$(whoami)/mcp-redacted/start-claude-code.sh
   Icon=/usr/share/icons/hicolor/scalable/apps/claude.svg
   Terminal=false
   Type=Application
   Categories=Development;
   EOF
   ```

   Note: If the icon path doesn't exist, you can omit that line or point to another icon.

6. **Verify Integration**

   After launching Claude with the MCP configuration:

   a. Use your configured Claude launcher

   b. Enter sensitive text (like an example credit card number: 4111-1111-1111-1111)

   c. This text should be automatically redacted before being sent to Claude

## Troubleshooting

If the integration doesn't work:

1. Check the log file:
   - `~/mcp-redacted/mcp_server.log`

2. Make sure the MCP server is running:
   ```bash
   ps aux | grep rules_engine_mcp.py
   ```

3. Test the MCP server with the test client:
   ```bash
   python improved_mcp_client.py
   ```

4. Ensure the configuration file has the correct paths for your system.

5. Check the Claude executable path and try running it manually:
   ```bash
   which claude
   # or
   which claude-code

   # Then run Claude with the MCP configuration
   claude --mcp-config=/path/to/claude-code-config.json
   ```

5. Check if the port 6366 is available and not blocked by a firewall:
   ```bash
   netstat -tuln | grep 6366
   ```

## Protocol Format

The Rules Engine MCP server uses the legacy "execute" protocol format:

```json
{
  "jsonrpc": "2.0",
  "method": "execute",
  "params": {
    "name": "tool_name",
    "parameters": {"param1": "value1"}
  },
  "id": 1
}
```

The Claude Code integration will automatically use this format when configured with the provided config file.