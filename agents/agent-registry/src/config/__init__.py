"""
Environment Configuration

Configuration settings loaded from environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "agent_registry")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "agents")

# Server configuration
REGISTRY_HOST = os.getenv("REGISTRY_HOST", "0.0.0.0")
REGISTRY_PORT = int(os.getenv("REGISTRY_PORT", "8080"))

# AgentCard fetching configuration
AGENTCARD_TIMEOUT = int(os.getenv("AGENTCARD_TIMEOUT", "10"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
