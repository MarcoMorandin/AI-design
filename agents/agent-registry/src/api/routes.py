"""
Agent Registry API Routes

FastAPI routes for the agent registry service.
"""

import logging
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks

from ..models import AgentRegistrationRequest, AgentDiscoveryResponse
from trento_agent_sdk.a2a.models.AgentCard import AgentCard
from ..utils.agentcard_client import fetch_agent_card
from ..utils.mongodb_storage import MongoDBStorage

logger = logging.getLogger(__name__)


class AgentRegistryRoutes:
    """Agent registry API routes."""

    def __init__(self, storage: MongoDBStorage):
        self.storage = storage

    async def register_agent(
        self, request: AgentRegistrationRequest, background_tasks: BackgroundTasks
    ) -> AgentCard:
        """Register an agent by URL - automatically fetches AgentCard data."""
        try:
            logger.info(f"Registering agent from URL: {request.url}")

            # Fetch agent card data
            agent_card = await fetch_agent_card(request.url)

            if not agent_card:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not fetch AgentCard from {request.url}/.well-known/agent.json",
                )

            # Update agent card URL to match the request URL
            agent_card.url = request.url.rstrip("/")

            # Save to MongoDB (URL is used as identifier)
            success = await self.storage.save_agent(agent_card)
            if not success:
                raise HTTPException(
                    status_code=500, detail="Failed to save agent to database"
                )

            logger.info(
                f"Successfully registered agent: {agent_card.name} at {agent_card.url}"
            )
            return agent_card

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering agent from {request.url}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Registration failed: {str(e)}"
            )

    async def list_agents(self) -> AgentDiscoveryResponse:
        """List all registered agents."""
        try:
            agents = await self.storage.list_agents()
            return AgentDiscoveryResponse(agents=agents, total_count=len(agents))
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to list agents: {str(e)}"
            )

    async def get_agent(self, agent_url: str) -> AgentCard:
        """Get specific agent information by URL."""
        agent = await self.storage.get_agent(agent_url)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    async def unregister_agent(
        self, agent_url: str, background_tasks: BackgroundTasks
    ) -> dict:
        """Unregister an agent."""
        # Check if agent exists by trying to get it
        agent = await self.storage.get_agent(agent_url)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        success = await self.storage.unregister_agent(agent_url)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to delete agent from database"
            )

        logger.info(f"Unregistered agent: {agent_url}")
        return {"message": f"Agent {agent_url} unregistered successfully"}

    async def refresh_agent_card(
        self, agent_url: str, background_tasks: BackgroundTasks
    ) -> dict:
        """Refresh AgentCard data for a specific agent."""
        agent = await self.storage.get_agent(agent_url)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        try:
            agent_card = await fetch_agent_card(agent_url)

            if agent_card:
                # Update the agent card with fresh data
                agent_card.url = agent_url  # Ensure URL matches

                # Save updated agent
                success = await self.storage.save_agent(agent_card)
                if not success:
                    raise HTTPException(
                        status_code=500, detail="Failed to update agent in database"
                    )

                logger.info(f"Refreshed AgentCard for {agent_url}")
                return {"message": f"AgentCard refreshed for {agent_url}"}
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not fetch AgentCard from {agent_url}/.well-known/agent.json",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing agent card for {agent_url}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to refresh agent card: {str(e)}"
            )

    async def get_service_info(self) -> dict:
        """Root endpoint with service information."""
        try:
            all_agents = await self.storage.list_agents()
            total_agents = len(all_agents)
        except Exception:
            total_agents = 0

        return {
            "service": "Simple Agent Registry",
            "version": "1.0.0",
            "description": "Simple registry for agent registration and discovery",
            "endpoints": {
                "register": "POST /register (with {url: 'agent_base_url'})",
                "list_agents": "GET /agents",
                "get_agent": "GET /agents/{agent_id}",
                "unregister": "DELETE /agents/{agent_id}",
                "refresh": "POST /refresh/{agent_id}",
            },
            "total_agents": total_agents,
        }

    async def health_check(self) -> dict:
        """Health check endpoint."""
        try:
            # Check MongoDB connection
            is_connected = self.storage.client is not None
            is_db_healthy = False

            if is_connected:
                try:
                    # Try to ping MongoDB
                    await self.storage.database.command("ping")
                    is_db_healthy = True
                except Exception as e:
                    logger.error(f"MongoDB health check failed: {e}")
                    is_db_healthy = False

            return {
                "status": "healthy" if is_db_healthy else "degraded",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "api": "healthy",
                    "database": "healthy" if is_db_healthy else "unhealthy",
                },
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }
