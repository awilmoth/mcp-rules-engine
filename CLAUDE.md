# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a Windows service and taskbar application that provide regex-based text redaction capabilities through the Model Context Protocol (MCP). The service is designed to redact sensitive information before sending text to LLMs, with a focus on integration with JetBrains IDEs.

## Architecture

The project consists of two main applications:

1. **Regex Redaction MCP Service** - A Windows service that runs in the background
   - Implements a FastAPI server exposing MCP endpoints
   - Uses regex patterns to detect and redact sensitive information
   - Runs as a Windows service that starts automatically with the computer

2. **Regex Redaction MCP Taskbar App** - A system tray application with UI
   - Provides a user interface for managing redaction patterns
   - Includes a test tool for checking redaction functionality
   - Implements the same MCP protocol server as the service

## Key Components

- **regex_redaction_mcp.py** - Core module containing redaction logic and MCP API endpoints
- **redaction_service.py** - Windows service wrapper around the core module
- **redaction_taskbar_app.py** - PyQt5-based taskbar application
- **patterns.json** - Configuration file storing regex patterns

## Build & Development

### Development in Windows

1. **Setup Virtual Environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run Directly for Development**:
   ```bash
   python run_direct.py
   ```

3. **Test the Service**:
   ```bash
   python test_redaction.py
   ```

4. **Run Taskbar App**:
   ```bash
   python redaction_taskbar_app.py
   ```

### Development in WSL

1. **Setup Environment**:
   ```bash
   python setup_wsl.py
   source activate.sh
   ```

2. **Build Windows Installer**:
   ```bash
   ./build.sh
   ```

3. **Run for Development**:
   ```bash
   python app/regex_redaction_mcp.py
   ```

### Building the Windows Service

1. **Build With PyInstaller**:
   ```bash
   python build_wsl.py  # for WSL
   # or
   python build_service.py  # for Windows
   ```

2. **Create Installer**:
   The build scripts will automatically create an installer using Inno Setup.

### Building the Taskbar App

```bash
python build_taskbar_app.py
```

## Testing

To test the MCP server functionality:

```bash
python test_redaction.py
```

The test script will:
1. Check if the server is running
2. Test redaction functionality
3. Display available patterns

## Adding New Redaction Patterns

Patterns can be added programmatically via the MCP API or by modifying the patterns.json file. Each pattern consists of:

- `pattern`: Regular expression pattern string
- `replacement`: Text to replace matches with
- `description`: Human-readable description
- `enabled`: Boolean flag to enable/disable the pattern

## MCP API Endpoints

The service exposes MCP tools on port 6366:

- `redact_text`: Redacts text based on configured patterns
- `get_patterns`: Gets list of all patterns
- `add_pattern`: Adds a new pattern
- `update_pattern`: Updates an existing pattern
- `delete_pattern`: Deletes a pattern
- `reset_patterns`: Resets patterns to defaults

## Requirements

- Windows 10 or later (for production)
- Python 3.8 or later
- FastAPI, Uvicorn, PyDantic
- PyQt5 (for taskbar app)
- PyWin32 (for Windows service)
- Wine and Inno Setup (for WSL builds)