# app/db/mongodb.py
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from app.core.config import settings
from bson import UuidRepresentation

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_manager = MongoDB()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    try:
        db_manager.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            uuidRepresentation='standard'
        )
        
        db_manager.db = db_manager.client[settings.MONGODB_DB_NAME]
        # Optional: Ping server to verify connection
        await db_manager.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB.")
    except Exception as e:
        logger.exception(f"Could not connect to MongoDB: {e}")
        # Decide if the app should fail to start if DB connection fails
        # raise

async def close_mongo_connection():
    if db_manager.client:
        logger.info("Closing MongoDB connection...")
        db_manager.client.close()
        logger.info("MongoDB connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        # This should ideally not happen if connect_to_mongo ran successfully
        logger.error("Database not initialized. Call connect_to_mongo first.")
        # Depending on strategy, could try reconnecting or raise an error
        # For simplicity here, we assume it's initialized at startup
        raise RuntimeError("Database connection is not available.")
    return db_manager.db


def get_summary_collection():
    db = get_database()
    return db[settings.MONGODB_SUMMARY_COLLECTION]

def get_upload_collection():
    db = get_database()
    return db[settings.MONGODB_UPLOAD_COLLECTION]