FROM python:3.11-slim

WORKDIR /app

# Install curl and jq for healthcheck
RUN apt-get update && apt-get install -y curl jq && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a directory for logs and data
RUN mkdir -p /app/data /app/logs

# Expose the port
EXPOSE 8080

# Set environment variables
ENV REGISTRY_PORT=8080
ENV REGISTRY_HOST=0.0.0.0
ENV MONGODB_URI=mongodb://mongodb:27017
ENV MONGODB_DATABASE=agent_registry
ENV MONGODB_COLLECTION=agents
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "run.py"]
