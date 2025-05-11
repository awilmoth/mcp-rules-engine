FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY smithery.json .

# Copy test scripts
COPY test_redaction.py .

# Create log directory
RUN mkdir -p logs
RUN mkdir -p app/RulesEngineMCP

# Expose port
EXPOSE 6366

# Run the MCP server
CMD ["python", "app/rules_engine_mcp_sse.py"]