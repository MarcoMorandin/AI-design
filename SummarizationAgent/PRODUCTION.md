# SummarizationAgent Production Deployment Guide

This guide provides instructions for deploying the SummarizationAgent in a production environment.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Environment Setup](#environment-setup)
3. [Configuration](#configuration)
4. [Deployment Options](#deployment-options)
5. [Monitoring](#monitoring)
6. [Security Considerations](#security-considerations)
7. [Troubleshooting](#troubleshooting)
8. [Scaling](#scaling)

## System Requirements

### Hardware Requirements
- CPU: 4 cores (minimum), 8+ cores (recommended)
- RAM: 8GB (minimum), 16GB+ (recommended)
- Disk Space: 20GB+ available storage

### Software Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git (for updates)
- Linux, macOS, or Windows with WSL2

## Environment Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd SummarizationAgent
```

### 2. Set Up Environment Variables
Copy the template environment file and fill in your values:
```bash
cp .env.template .env
```

Edit the `.env` file with your API keys and configuration:
```bash
# Required API keys
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Environment (production, staging, development)
ENVIRONMENT=production

# Set appropriate chunk sizes for your use case
MAX_LENGTH_PER_CHUNK=30000
MAX_TOKEN_PER_CHUNK_GROUPED=2048
OVERLAPP_CHUNK=500
```

### 3. Set Permissions for Deploy Script
```bash
chmod +x deploy.sh
```

## Configuration

### Chunker Configuration
The chunking module has two algorithms available:
- **Standard Chunker**: Simple token-based text splitting
- **Cosine Chunker**: Semantic chunking using embeddings and cosine similarity

Set the preferred chunker in your `.env` file:
```bash
CHUNCKER_TYPE=cosine  # Options: standard, cosine
```

### Logging Configuration
Adjust logging settings in the `.env` file:
```bash
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
ENABLE_METRICS=True
```

Logs are stored in the `./logs` directory and are rotated automatically to prevent disk space issues.

## Deployment Options

### Using the Deployment Script

The included `deploy.sh` script provides commands for managing the service:

```bash
# Start the service
./deploy.sh start

# Start with monitoring (Prometheus + Grafana)
./deploy.sh start-monitoring

# Check service status
./deploy.sh status

# View logs
./deploy.sh logs
# Follow logs in real-time
./deploy.sh logs follow

# Stop the service
./deploy.sh stop

# Update and rebuild
./deploy.sh update
./deploy.sh restart
```

### Manual Docker Compose Commands

If you prefer not to use the script:

```bash
# Start the service
docker-compose up -d summarization-agent

# Start with monitoring
docker-compose --profile monitoring up -d

# Check logs
docker-compose logs -f summarization-agent

# Stop services
docker-compose down
```

## Monitoring

### Health Checks
The service exposes a `/health` endpoint that returns service health information, useful for monitoring and container orchestration platforms.

### Prometheus Metrics
When started with the monitoring profile, the service includes:
- **Prometheus** (http://localhost:9090): Collects and stores metrics
- **Grafana** (http://localhost:3000): Visualizes metrics with dashboards

Default Grafana login:
- Username: admin
- Password: admin (change this in production)

## Security Considerations

### API Key Management
- **Never commit API keys** to version control
- Use environment variables or secure key management solutions
- Rotate keys periodically

### Network Security
- The service binds to `0.0.0.0` to allow container access
- Use a reverse proxy (e.g., Nginx) in front of the service
- Configure TLS/SSL for production traffic
- Implement appropriate firewall rules

### Container Security
- The Dockerfile runs the service as a non-root user (`appuser`)
- Keep Docker and dependencies updated
- Scan container images for vulnerabilities

## Troubleshooting

### Common Issues

**Service doesn't start:**
1. Check if required API keys are set in `.env`
2. Verify Docker and Docker Compose are running
3. Check logs: `./deploy.sh logs`

**Memory issues:**
1. Increase container memory limits in `docker-compose.yml`
2. Reduce `MAX_LENGTH_PER_CHUNK` and `MAX_TOKEN_PER_CHUNK_GROUPED` values

**Slow performance:**
1. Check CPU and memory usage
2. Consider using `standard` chunker if `cosine` is too resource-intensive
3. Consider scaling the service horizontally

### Getting Help
If you encounter persistent issues:
1. Check the Docker and service logs
2. Review configuration settings
3. Open an issue in the repository with detailed information

## Scaling

### Vertical Scaling
Adjust resources in the `docker-compose.yml` file:
```yaml
services:
  summarization-agent:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

### Horizontal Scaling
For high-demand scenarios, consider:
1. Running multiple instances behind a load balancer
2. Implementing a distributed processing pattern with message queues
3. Using Kubernetes for container orchestration