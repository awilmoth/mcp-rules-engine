# Deploying to Smithery

Based on the current Smithery CLI behavior, it appears that deployment has changed since our scripts were created. Here's the recommended approach for deploying to Smithery:

## Option 1: Direct Repository Upload

1. Go to the Smithery web interface: https://smithery.ai
2. Log in to your account
3. Navigate to the "Servers" or "Deployments" section
4. Click "Add New" or "Deploy"
5. Select "GitHub Repository" as the source
6. Connect to your GitHub account if needed
7. Select the `mcp-rules-engine` repository
8. Follow the prompts to complete deployment

## Option 2: Manual Package Upload

1. Go to the Smithery web interface: https://smithery.ai
2. Log in to your account
3. Navigate to the "Servers" or "Deployments" section
4. Click "Add New" or "Deploy"
5. Select "Manual Upload" as the source
6. Upload the `rules_engine_mcp.zip` file we created
7. Follow the prompts to complete deployment

## Option 3: CLI Deployment (If Web Interface Not Available)

Try these commands:

```bash
# Install with explicit path
npx -y @smithery/cli@latest install @awilmoth/mcp-rules-engine --key YOUR_API_KEY --client claude

# Or try with full repository URL
npx -y @smithery/cli@latest install https://github.com/awilmoth/mcp-rules-engine --key YOUR_API_KEY --client claude
```

## After Deployment

Once deployed to Smithery, you can interact with your MCP server through:

1. The Smithery web interface
2. The Smithery API using your API key
3. Via Claude or other integrated AI clients

## Troubleshooting

If deployment continues to fail:

1. Verify your API key is correct and has the necessary permissions
2. Check if there are any special requirements for MCP servers on Smithery
3. Contact Smithery support for assistance with deployment

## Local Testing

Remember that your local MCP server is fully functional and can be used in the meantime:

```bash
# Start the server
./run_mcp_server.sh

# Test redaction
./use_direct_redaction.sh "My SSN is 123-45-6789"
```