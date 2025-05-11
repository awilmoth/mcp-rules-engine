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

# Copy minimal application code needed for Smithery deployments
COPY app/rules_engine_mcp_sse.py app/
COPY app/RulesEngineMCP/rules_config.json app/RulesEngineMCP/

# Create log directory
RUN mkdir -p logs app/RulesEngineMCP/logs

# Expose port
EXPOSE 6366

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6366/health || exit 1

# Run the MCP server
CMD ["python", "app/rules_engine_mcp_sse.py"]