# Agent Registry Service

A registry service for agent discovery and management in the AI-design ecosystem.

## Overview

The Agent Registry Service enables the dynamic registration, discovery, and management of AI agents in a distributed system. It maintains a catalog of available agents with their capabilities, providing a central point for orchestrators and clients to discover and interact with various specialized agents.

## Features

- **Agent Registration**: Register agents by URL, automatically fetching their AgentCard metadata
- **Agent Discovery**: Query the registry to find agents with specific capabilities
- **Agent Management**: Update, refresh, and unregister agents as needed
- **Persistent Storage**: MongoDB-based storage for agent information

## Prerequisites

- Python 3.9 or higher
- MongoDB (local or remote)
- Docker (for containerized deployment)

## Configuration

The service is configured via environment variables, which can be set directly or through a `.env` file:

```
# MongoDB configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=agent_registry
MONGODB_COLLECTION=agents

# Server configuration
HOST=0.0.0.0
PORT=8080

# Logging
LOG_LEVEL=INFO
```

## API Endpoints

### Register an Agent

Register a new agent by providing its base URL:

```bash
curl -X POST "http://localhost:8080/register" \
-H "Content-Type: application/json" \
-d '{
    "url": "https://your-agent-service-url.com"
}'
```

The service will automatically fetch the agent's capabilities by accessing the `/.well-known/agent.json` endpoint at the provided URL.

### List All Registered Agents

Retrieve a list of all registered agents:

```bash
curl -X GET "http://localhost:8080/agents"
```

### Get Specific Agent

Get details about a specific agent by URL:

```bash
curl -X GET "http://localhost:8080/agents/https%3A%2F%2Fyour-agent-service-url.com"
```

Note: The URL must be URL-encoded.

### Refresh Agent Metadata

Force a refresh of an agent's metadata:

```bash
curl -X POST "http://localhost:8080/refresh/https%3A%2F%2Fyour-agent-service-url.com"
```

### Unregister an Agent

Remove an agent from the registry:

```bash
curl -X DELETE "http://localhost:8080/agents/https%3A%2F%2Fyour-agent-service-url.com"
```

## Docker Deployment

### Build the Docker Image

```bash
docker build -t agent-registry .
```

### Run the Container

```bash
docker run -p 8080:8080 \
  -e MONGODB_URI=mongodb://mongo:27017 \
  -e MONGODB_DATABASE=agent_registry \
  -e MONGODB_COLLECTION=agents \
  --name agent-registry \
  agent-registry
```

## Integration with AI-design System

The Agent Registry serves as the central directory for the AI-design system's orchestrator to discover specialized agents. When new capabilities are added to the system:

1. Register the new agent with the registry
2. The orchestrator can now discover and utilize the new agent's capabilities

## Developing New Agents

For an agent to be discoverable by the registry, it must expose an AgentCard at the `/.well-known/agent.json` endpoint. The AgentCard should follow the schema defined in the `trento-agent-sdk` library.

Example AgentCard:

```json
{
  "name": "PDF Summarizer Agent",
  "description": "Summarizes PDF documents",
  "url": "https://your-agent-service-url.com",
  "version": "1.0.0",
  "skills": [
    {
      "id": "summarize-pdf",
      "name": "Summarize PDF",
      "description": "Creates concise summaries of PDF documents",
      "examples": [
        "Summarize this PDF: report.pdf"
      ]
    }
  ],
  "default_input_modes": ["text/plain"],
  "default_output_modes": ["text/plain"],
  "provider": "University of Trento",
  "documentation_url": "https://your-docs-url.com"
}
```

## License

This project is licensed under the terms specified in the repository's LICENSE file.
