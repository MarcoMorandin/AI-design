FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m appuser
USER appuser

# Expose the port the app runs on
EXPOSE 8002

# Command to run the application
CMD ["python", "rag_a2a_server.py"]
