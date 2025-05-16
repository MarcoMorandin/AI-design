FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Add non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install curl for healthcheck and any additional requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variable to indicate production
ENV ENVIRONMENT=production

# Set PORT variable for Google Cloud Run compatibility
ENV PORT=8080
ENV WEBHOOK_SERVICE_PORT=8080

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Expose the service port (dynamic from env, default to 8080 for Cloud Run)
EXPOSE ${PORT:-8080}

# Start the application
CMD exec python main.py