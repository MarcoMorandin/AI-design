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

# Expose the port
EXPOSE 8080

# Run the application
CMD ["python", "run.py"]
