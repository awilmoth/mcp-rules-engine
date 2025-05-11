# Smithery Integration Guide

This document explains how to integrate your MCP Rules Engine with Smithery for cloud hosting and enhanced AI features.

## Overview

Smithery provides:
- Cloud hosting for your MCP server
- Direct integration with Claude and other AI services
- Configuration management
- Analytics and monitoring

## Prerequisites

1. [Smithery](https://smithery.ai) account
2. API key from Smithery dashboard
3. Your MCP Rules Engine from this repository

## Setup

### 1. Install Required Tools

The script `smithery_setup.sh` handles Smithery CLI interactions. Make sure it's executable:

```bash
chmod +x smithery_setup.sh
```

### 2. Install MCP Server to Smithery

Install your MCP server to Smithery using your API key:

```bash
./smithery_setup.sh install YOUR_SMITHERY_API_KEY
```

This will:
- Create the deployment package if needed
- Install your MCP server to Smithery
- Connect to the Claude client

### 3. Run MCP Server Locally with Smithery Integration

Start your local MCP server with Smithery integration:

```bash
./smithery_setup.sh run
```

### 4. Check Installed Servers and Clients

List available clients and installed servers:

```bash
./smithery_setup.sh list
```

### 5. Test Redaction

Test the redaction functionality:

```bash
./smithery_setup.sh test "My SSN is 123-45-6789 and my email is test@example.com"
```

## Using with Claude

After setting up Smithery, you can use Claude with your MCP Rules Engine:

```bash
# Directly via Smithery API
curl -H "Authorization: Bearer YOUR_SMITHERY_API_KEY" \
  https://api.smithery.ai/v1/claude/text \
  -d '{"text":"My SSN is 123-45-6789"}'

# Or via tools compatible with Smithery
```

## Troubleshooting

### Common Issues

1. **Installation Fails**: Check your API key and ensure it has the necessary permissions

2. **Connection Issues**: Verify your network connection and that the Smithery API is accessible

3. **Claude Integration Fails**: Make sure you've installed the Claude connector

### Getting Help

For additional help:
- Check Smithery documentation: https://docs.smithery.ai
- Contact Smithery support: support@smithery.ai

## Next Steps

After setting up Smithery integration:

1. Create custom rule sets for different use cases
2. Configure specific redaction patterns
3. Set up monitoring and analytics
4. Integrate with your applications

For more information, see the Smithery dashboard and documentation.