FROM python:3.11-slim

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
ENV PORT=6371
ENV HOST=0.0.0.0

# Copy server files
COPY smithery_scan_server.py .
COPY simple_mcp_server.py .
COPY smithery.yaml .

# Create logs directory
RUN mkdir -p logs

# Expose ports
EXPOSE 6366
EXPOSE 6371

# Health check to ensure the service is responding
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -s -f http://localhost:6371/health || exit 1

# For Smithery compatibility, run the scan server first
CMD ["python", "smithery_scan_server.py"]