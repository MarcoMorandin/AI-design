"""
MongoDB Storage

MongoDB-based storage implementation for agent registry using AgentCard with URL as identifier.
"""

import logging
from typing import List, Optional
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)

from trento_agent_sdk.a2a.models.AgentCard import AgentCard
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

    async def save_agent(self, agent_card: AgentCard) -> bool:
        """Save agent information to MongoDB (create or update)."""
        try:
            # Use URL as the unique identifier
            await self.collection.replace_one(
                {"url": agent_card.url}, agent_card.dict(), upsert=True
            )
            logger.info(f"Saved agent: {agent_card.name} at {agent_card.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to save agent: {e}")
            return False

    async def get_agent(self, agent_url: str) -> Optional[AgentCard]:
        """Get agent information by URL."""
        try:
            document = await self.collection.find_one({"url": agent_url})
            if document:
                # Remove MongoDB's _id field if present
                document.pop("_id", None)
                agent_card = AgentCard(**document)
                return agent_card
            return None
        except Exception as e:
            logger.error(f"Failed to get agent {agent_url}: {e}")
            return None

    async def list_agents(self) -> List[AgentCard]:
        """List all registered agents."""
        try:
            cursor = self.collection.find({})
            documents = await cursor.to_list(length=None)

            # Remove MongoDB's _id field from each document
            for doc in documents:
                doc.pop("_id", None)

            agent_cards = [AgentCard(**doc) for doc in documents]
            return agent_cards
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []

    async def unregister_agent(self, agent_url: str) -> bool:
        """Unregister (delete) an agent from MongoDB."""
        try:
            result = await self.collection.delete_one({"url": agent_url})
            if result.deleted_count > 0:
                logger.info(f"Unregistered agent: {agent_url}")
                return True
            else:
                logger.warning(f"Agent {agent_url} not found for deletion")
                return False
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_url}: {e}")
            return False
