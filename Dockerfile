# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY start.py ./
COPY .env* ./

# Create logs directory
RUN mkdir -p logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health', timeout=5)" || exit 1

# Expose port
EXPOSE 8080

# Default command (can be overridden)
CMD ["python", "start.py"]

