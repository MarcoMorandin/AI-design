FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variable to indicate production
ENV ENVIRONMENT=production

# Expose the service port
EXPOSE 5000

# Start the application
CMD ["python", "main.py"]