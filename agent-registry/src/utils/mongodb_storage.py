"""
MongoDB Storage

MongoDB-based storage implementation for agent registry.
"""

import logging
from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)

from ..models import AgentInfo
from ..config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION

logger = logging.getLogger(__name__)


class MongoDBStorage:
    """MongoDB storage implementation for agent registry."""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.collection: Optional[AsyncIOMotorCollection] = None

    async def connect(self):
        """Connect to MongoDB."""
        try:
            logger.info(f"Connecting to MongoDB at {MONGODB_URI}")
            self.client = AsyncIOMotorClient(MONGODB_URI)
            self.database = self.client[MONGODB_DATABASE]
            self.collection = self.database[MONGODB_COLLECTION]
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def register_agent(self, agent_info: AgentInfo) -> AgentInfo:
        """Register an agent in MongoDB."""
        try:
            # Set timestamps
            agent_info.created_at = datetime.utcnow()
            agent_info.updated_at = agent_info.created_at

            # Insert into MongoDB
            await self.collection.insert_one(agent_info.dict())
            logger.info(f"Registered agent: {agent_info.name} ({agent_info.id})")
            return agent_info
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            raise

    async def save_agent(self, agent_info: AgentInfo) -> bool:
        """Save agent information to MongoDB (create or update)."""
        try:
            # Check if agent already exists
            existing_agent = await self.get_agent(agent_info.agent_id)

            if existing_agent:
                # Update timestamp for last_seen
                agent_info.last_seen = datetime.utcnow()

                # Update in MongoDB
                await self.collection.replace_one(
                    {"agent_id": agent_info.agent_id}, agent_info.dict()
                )
                logger.info(f"Updated agent: {agent_info.name} ({agent_info.agent_id})")
            else:
                # Insert into MongoDB
                await self.collection.insert_one(agent_info.dict())
                logger.info(
                    f"Registered agent: {agent_info.name} ({agent_info.agent_id})"
                )

            return True
        except Exception as e:
            logger.error(f"Failed to save agent: {e}")
            return False

    async def update_agent(self, agent_id: str, agent_info: AgentInfo) -> AgentInfo:
        """Update an agent in MongoDB."""
        try:
            # Update timestamp
            agent_info.updated_at = datetime.utcnow()

            # Update in MongoDB
            await self.collection.replace_one({"id": agent_id}, agent_info.dict())
            logger.info(f"Updated agent: {agent_info.name} ({agent_info.id})")
            return agent_info
        except Exception as e:
            logger.error(f"Failed to update agent: {e}")
            raise

    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get an agent by ID from MongoDB."""
        try:
            document = await self.collection.find_one({"agent_id": agent_id})
            if not document:
                logger.warning(f"Agent not found: {agent_id}")
                return None

            agent_info = AgentInfo(**document)
            logger.info(f"Retrieved agent: {agent_info.name} ({agent_info.agent_id})")
            return agent_info
        except Exception as e:
            logger.error(f"Failed to get agent: {e}")
            raise

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from MongoDB."""
        try:
            result = await self.collection.delete_one({"agent_id": agent_id})
            if result.deleted_count == 0:
                logger.warning(f"Agent not found for unregistering: {agent_id}")
                return False

            logger.info(f"Unregistered agent: {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister agent: {e}")
            raise

    async def list_agents(self) -> List[AgentInfo]:
        """List all agents from MongoDB."""
        try:
            cursor = self.collection.find({})
            documents = await cursor.to_list(length=100)
            agent_infos = [AgentInfo(**doc) for doc in documents]
            logger.info(f"Listed {len(agent_infos)} agents")
            return agent_infos
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            raise

    async def count_agents(self) -> int:
        """Count the number of registered agents."""
        try:
            count = await self.collection.count_documents({})
            logger.info(f"Counted {count} agents")
            return count
        except Exception as e:
            logger.error(f"Failed to count agents: {e}")
            raise
