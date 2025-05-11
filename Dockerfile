FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY smithery.json .
COPY server.py .

# Copy config and rules
COPY app/RulesEngineMCP/ app/RulesEngineMCP/

# Copy test scripts
COPY test_redaction.py .
COPY test_mcp.py .

# Create log directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=6366

# Expose port
EXPOSE 6366

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6366/health || exit 1

# Run the MCP server
CMD ["python", "app/rules_engine_mcp_sse.py"]