FROM python:3.11

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p config/credentials dashboard_data \
    && chmod -R 777 config/credentials dashboard_data

# Set Python path
ENV PYTHONPATH=/app

# Set default environment variables
ENV ES_HOST=http://helpdesk_elasticsearch:9200 \
    ES_INDEX=tickets \
    DEBUG_MODE=False \
    POLL_INTERVAL_SECONDS=15

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://elasticsearch:9200 || exit 1

# Command to run the application
CMD ["python", "-m", "src.main"] 