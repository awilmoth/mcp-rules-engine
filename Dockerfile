FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
# Use pip cache for faster rebuilds
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables early for better caching
ENV PYTHONUNBUFFERED=1
ENV PORT=6366

# Copy core server logic first (changes less frequently)
COPY server.py .
COPY smithery.json .
COPY smithery.yaml .

# Copy minimal application code needed for Smithery deployments
COPY app/rules_engine_mcp_sse.py app/
COPY app/RulesEngineMCP/rules_config.json app/RulesEngineMCP/

# Create log directory
RUN mkdir -p logs app/RulesEngineMCP/logs

# Expose port
EXPOSE 6366

# Health check to ensure the service is responding
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -s -f http://localhost:6366/health || exit 1

# For Smithery compatibility, run server.py instead of the direct MCP script
# This allows for proper tool scanning and lazy loading
CMD ["python", "server.py"]