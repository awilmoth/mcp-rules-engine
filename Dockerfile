FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=6366
ENV HOST=0.0.0.0

# Copy application files
COPY smithery_scan_server.py .
COPY simple_mcp_server.py .
COPY smithery_deployment/rules_engine_mcp_sse.py .
COPY rules_config.json ./RulesEngineMCP/

# Create necessary directories
RUN mkdir -p logs
RUN mkdir -p RulesEngineMCP

# Expose the MCP port
EXPOSE 6366

# Health check to ensure the service is responding
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -s -f http://localhost:6366/health || exit 1

# For Smithery compatibility, run the scan server first
CMD ["python", "smithery_scan_server.py"]