FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m appuser
USER appuser

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["python", "orchestrator.py"]
