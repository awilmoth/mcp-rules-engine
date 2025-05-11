FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy stdio server and dependencies
COPY stdio_server.py .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p logs

# Set environment variables for unbuffered output
ENV PYTHONUNBUFFERED=1
ENV MCP_STDIO_TRANSPORT=true

# Start the STDIO server
CMD ["python", "-u", "stdio_server.py"]