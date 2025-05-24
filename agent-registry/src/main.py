#!/usr/bin/env python3
"""
Simple Agent Registry Service - Main Application

This service provides:
- Simple POST endpoint to register agents by URL
- Automatically fetches AgentCard data from /.well-known/agent.json
- Discovery endpoint for finding agents
- Persistent storage of agent information in MongoDB
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .models import AgentRegistrationRequest, AgentDiscoveryResponse
from trento_agent_sdk.a2a.models.AgentCard import AgentCard
from .utils.mongodb_storage import MongoDBStorage
from .api.routes import AgentRegistryRoutes
from .config import REGISTRY_HOST, REGISTRY_PORT, LOG_LEVEL

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global storage instance
storage = MongoDBStorage()
routes_handler = AgentRegistryRoutes(storage)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting Agent Registry Service...")
    await storage.connect()
    logger.info("Agent Registry Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Agent Registry Service...")
    await storage.disconnect()
    logger.info("Agent Registry Service shut down successfully")


def create_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Simple Agent Registry Service",
        description="Simple registry for agent registration and discovery with MongoDB storage",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    @app.post("/register", response_model=AgentCard)
    async def register_agent(
        request: AgentRegistrationRequest, background_tasks: BackgroundTasks
    ):
        """Register an agent by URL - automatically fetches AgentCard data."""
        return await routes_handler.register_agent(request, background_tasks)

    @app.get("/agents", response_model=AgentDiscoveryResponse)
    async def list_agents():
        """List all registered agents."""
        return await routes_handler.list_agents()

    @app.get("/agents/{agent_url:path}", response_model=AgentCard)
    async def get_agent(agent_url: str):
        """Get specific agent information by URL."""
        return await routes_handler.get_agent(agent_url)

    @app.delete("/agents/{agent_url:path}")
    async def unregister_agent(agent_url: str, background_tasks: BackgroundTasks):
        """Unregister an agent."""
        return await routes_handler.unregister_agent(agent_url, background_tasks)

    @app.post("/refresh/{agent_url:path}")
    async def refresh_agent_card(agent_url: str, background_tasks: BackgroundTasks):
        """Refresh AgentCard data for a specific agent."""
        return await routes_handler.refresh_agent_card(agent_url, background_tasks)

    @app.get("/")
    async def root():
        """Root endpoint with service information."""
        return await routes_handler.get_service_info()

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return await routes_handler.health_check()

    return app


def main():
    """Main entry point."""
    app = create_app()
    logger.info(f"Starting Simple Agent Registry on {REGISTRY_HOST}:{REGISTRY_PORT}")
    uvicorn.run(
        app, host=REGISTRY_HOST, port=REGISTRY_PORT, log_level=LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
