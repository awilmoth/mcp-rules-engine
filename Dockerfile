FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy minimal server and dependencies
COPY minimal_server.py .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 6366

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -s -f http://localhost:6366/health || exit 1

# Start the minimal server
CMD ["python", "-u", "minimal_server.py"]