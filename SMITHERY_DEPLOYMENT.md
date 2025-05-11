# Deploying MCP Rules Engine to Smithery

This document provides instructions for deploying your MCP Rules Engine to Smithery's cloud platform for seamless integration with Claude and other AI tools.

## Benefits of Smithery Deployment

1. **Hosted Infrastructure**: No need to maintain your own server
2. **Scalable Performance**: Handles high load with serverless architecture
3. **Native Integration**: Connect directly to Claude and other AI tools
4. **Managed Updates**: Smithery handles platform updates and security
5. **Configuration Management**: Manage redaction rules through UI

## Preparation

Run the included preparation script:

```bash
./prepare_smithery_deployment.sh
```

This will:
1. Create a `smithery.json` configuration file
2. Package your MCP server code for deployment
3. Create a deployment ZIP file (`rules_engine_mcp.zip`)

## Deployment Steps

1. **Create Smithery Account**
   - Sign up at [smithery.ai](https://smithery.ai)
   - Verify your email and complete your profile

2. **Deploy Your Server**
   - Navigate to "Deployments" in the dashboard
   - Click "Add Server"
   - Upload the `rules_engine_mcp.zip` file
   - Follow the prompts to configure your deployment

3. **Configure Deployment**
   - Name: "Rules Engine MCP"
   - Description: "Regex-based sensitive information redaction"
   - Configure the default rule set if desired

4. **Test Your Deployment**
   - Use the Smithery UI to test redaction with example text
   - Verify all your supported patterns are working correctly

## Integration with Claude

1. **Get API Key**
   - In Smithery dashboard, go to "API Keys"
   - Create a new key for Claude integration
   - Copy the key for configuration

2. **Configure Integration**
   - Run `./use_smithery.sh configure`
   - Enter your Smithery API key
   - Set Smithery as the primary redaction service

3. **Usage**
   - Redact text: `./use_smithery.sh redact "Text with sensitive info"`
   - Redact and send to Claude: `./use_smithery.sh claude "Text with sensitive info"`

## How It Works

Your MCP server deployed on Smithery operates via HTTP transport, allowing for:

1. **Stateless Operation**: Each request is processed independently
2. **Serverless Execution**: Runs only when needed, scales automatically
3. **Config Management**: Updates to rules are managed through the Smithery UI
4. **Native Claude Integration**: Uses Smithery's direct connection to Claude

## Customization

You can enhance your deployment by:

1. **Custom Rule Sets**: Create specialized rule sets for different contexts
2. **Extended Patterns**: Add industry-specific patterns like medical terms
3. **Whitelisting**: Configure exception patterns for false positives

## Support

For support with your Smithery deployment:
- Smithery Documentation: https://docs.smithery.ai
- Smithery Support: support@smithery.ai