"""
Agent Registry API Routes

FastAPI routes for the agent registry service.
"""

import logging
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks

from ..models import AgentRegistrationRequest, AgentInfo, AgentDiscoveryResponse
from ..utils.agentcard_client import fetch_agent_card
from ..utils.mongodb_storage import MongoDBStorage

logger = logging.getLogger(__name__)


class AgentRegistryRoutes:
    """Agent registry API routes."""

    def __init__(self, storage: MongoDBStorage):
        self.storage = storage

    def _generate_agent_id(self, name: str) -> str:
        """Generate a simple agent ID from the name."""
        base_id = name.lower().replace(" ", "-").replace("_", "-")
        # Remove non-alphanumeric characters except hyphens
        base_id = "".join(c for c in base_id if c.isalnum() or c == "-")

        return base_id

    async def register_agent(
        self, request: AgentRegistrationRequest, background_tasks: BackgroundTasks
    ) -> AgentInfo:
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

            # Generate agent ID if not provided
            agent_id = request.agent_id or self._generate_agent_id(agent_card.name)

            # Check if agent already exists to preserve registration time
            existing_agent = await self.storage.get_agent(agent_id)
            registered_at = (
                existing_agent.registered_at if existing_agent else datetime.now()
            )

            # Create agent info
            agent_info = AgentInfo(
                agent_id=agent_id,
                name=agent_card.name,
                description=agent_card.description,
                url=request.url.rstrip("/"),
                version=agent_card.version,
                skills=agent_card.skills,
                provider=agent_card.provider,
                registered_at=registered_at,
                last_seen=datetime.now(),
                status="active",
            )

            # Save to MongoDB
            success = await self.storage.save_agent(agent_info)
            if not success:
                raise HTTPException(
                    status_code=500, detail="Failed to save agent to database"
                )

            logger.info(
                f"Successfully registered agent: {agent_id} ({agent_card.name})"
            )
            return agent_info

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

    async def get_agent(self, agent_id: str) -> AgentInfo:
        """Get specific agent information."""
        agent = await self.storage.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    async def unregister_agent(
        self, agent_id: str, background_tasks: BackgroundTasks
    ) -> dict:
        """Unregister an agent."""
        # Check if agent exists by trying to get it
        agent = await self.storage.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        success = await self.storage.unregister_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to delete agent from database"
            )

        logger.info(f"Unregistered agent: {agent_id}")
        return {"message": f"Agent {agent_id} unregistered successfully"}

    async def refresh_agent_card(
        self, agent_id: str, background_tasks: BackgroundTasks
    ) -> dict:
        """Refresh AgentCard data for a specific agent."""
        agent = await self.storage.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        try:
            agent_card = await fetch_agent_card(agent.url)

            if agent_card:
                # Update the agent with fresh data
                agent.name = agent_card.name
                agent.description = agent_card.description
                agent.version = agent_card.version
                agent.skills = agent_card.skills
                agent.provider = agent_card.provider
                agent.last_seen = datetime.now()
                agent.status = "active"

                # Save updated agent
                success = await self.storage.save_agent(agent)
                if not success:
                    raise HTTPException(
                        status_code=500, detail="Failed to update agent in database"
                    )

                logger.info(f"Refreshed AgentCard for {agent_id}")
                return {"message": f"AgentCard refreshed for {agent_id}"}
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not fetch AgentCard from {agent.url}/.well-known/agent.json",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing agent card for {agent_id}: {e}")
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
