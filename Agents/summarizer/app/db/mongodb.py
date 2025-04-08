# app/db/mongodb.py
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global variables for database connection
client: AsyncIOMotorClient = None
database: AsyncIOMotorDatabase = None

async def connect_to_mongo():
    """Create database connection."""
    global client, database
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = client[settings.MONGODB_DB_NAME]
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection."""
    global client
    if client:
        client.close()
        logger.info("Closed MongoDB connection")

def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    return database

def get_task_collection() -> AsyncIOMotorCollection:
    """Get tasks collection."""
    return database["tasks"]

def get_summary_collection() -> AsyncIOMotorCollection:
    """Get summaries collection."""
    return database["summaries"]