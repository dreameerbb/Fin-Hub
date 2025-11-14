# Portfolio Spoke - MCP HTTP/SSE Mode
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (numpy/scipy need these)
RUN apt-get update && apt-get install -y \
    gcc \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ./services/portfolio-spoke/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the entire project structure (needed for imports)
COPY . /app/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8003/health')" || exit 1

# Expose port
EXPOSE 8003

# Start MCP HTTP/SSE server
CMD ["python", "/app/services/portfolio-spoke/mcp_server_http.py", "--host", "0.0.0.0", "--port", "8003"]
