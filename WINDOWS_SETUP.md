# Windows Setup for Claude Desktop Integration

This guide will help you set up the Rules Engine MCP server to work with Claude Desktop on Windows.

## Prerequisites

- Python 3.8 or later installed on Windows
- Claude Desktop installed
- Administrator privileges (for service installation)

## Installation Steps

1. **Clone or extract the repository to your Windows machine**
   
   Extract this repository to a location such as `C:\Users\YOUR_USERNAME\mcp-redacted` or wherever you prefer.

2. **Set up a Python virtual environment**
   
   Open Command Prompt or PowerShell and run:
   ```
   cd %USERPROFILE%\mcp-redacted
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Test the Rules Engine MCP Server**
   
   Start the MCP server manually:
   ```
   venv\Scripts\activate
   python app\rules_engine_mcp.py
   ```
   
   Open another Command Prompt and run the test client:
   ```
   venv\Scripts\activate
   python windows_mcp_client.py
   ```
   
   If the test client successfully connects and redacts text, the server is working.

4. **Configure Claude Desktop**

   There are two ways to run Claude Desktop with the Rules Engine MCP server:

   a. **Manual Launch**

      Use the `start-claude-desktop.bat` script to start both the MCP server and Claude Desktop:
      ```
      %USERPROFILE%\mcp-redacted\start-claude-desktop.bat
      ```

      This script:
      - Checks if the MCP server is running and starts it if needed
      - Looks for Claude Desktop in common installation paths (Program Files and Program Files (x86))
      - If not found, prompts for the path to Claude.exe
      - Launches Claude Desktop with the proper MCP configuration

      If Claude Desktop isn't found, the script will still start the MCP server and provide instructions for manually running Claude Desktop with the configuration.
   
   b. **Automatic Launch as a Windows Service** (recommended)
      
      i. Download and install NSSM (Non-Sucking Service Manager) from https://nssm.cc/download
      
      ii. Run the service setup script as administrator:
      ```
      Right-click on setup-windows-service.bat and select "Run as administrator"
      ```
      
      iii. Configure Claude Desktop to use the MCP configuration:
      ```
      "C:\Program Files\Claude\Claude.exe" --mcp-config="%USERPROFILE%\mcp-redacted\claude-desktop-config.json"
      ```
      
      iv. Create a desktop shortcut with this command line.

5. **Verify Integration**

   After launching Claude Desktop with the MCP configuration:
   
   a. Open Claude Desktop
   
   b. Enter sensitive text (like an example credit card number: 4111-1111-1111-1111)
   
   c. This text should be automatically redacted before being sent to Claude

## Troubleshooting

If the integration doesn't work:

1. Check the log files:
   - `%USERPROFILE%\mcp-redacted\mcp_server.log`
   - `%USERPROFILE%\mcp-redacted\mcp_server_error.log` (if running as a service)

2. Make sure the MCP server is running:
   - Open Task Manager and look for a Python process running rules_engine_mcp.py
   - If running as a service, check Services management console (services.msc)

3. Test the MCP server with the test client:
   ```
   python windows_mcp_client.py
   ```

4. Ensure the configuration file has the correct paths for your system.

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

The Claude Desktop integration will automatically use this format when configured with the provided config file.