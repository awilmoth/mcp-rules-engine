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

# Copy necessary files
COPY simple_mcp_stdio.py .
COPY redact_text.py .
COPY server.py .
COPY smithery.yaml .

# Create logs directory
RUN mkdir -p logs

# Make script executable
RUN chmod +x simple_mcp_stdio.py

# Default command will be overridden by smithery.yaml
# Default to STDIO mode for Smithery compatibility
CMD ["python", "-u", "simple_mcp_stdio.py", "--stdio"]