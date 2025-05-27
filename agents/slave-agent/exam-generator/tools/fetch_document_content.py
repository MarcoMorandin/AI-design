from typing import Dict, Any, List
import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

load_dotenv()
logger = logging.getLogger(__name__)

# Get database configuration from environment
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGODB_DB_NAME", "drive_documents")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION", "processed_files")


async def fetch_document_content(document_id: str) -> Dict[str, Any]:
    """
    Fetches document content from MongoDB based on the Google Drive file ID.

    Args:
        document_id: The Google Drive file ID to retrieve

    Returns:
        Dict containing the document content, success status and message

    Tool:
        name: fetch_document_content
        description: Retrieves document content from MongoDB by Google Drive file ID
    """
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[COLLECTION_NAME]

        # Find document by Google Drive ID
        document = collection.find_one({"google_document_id": document_id})

        # Close MongoDB connection
        client.close()

        if not document:
            logger.error(f"Document with ID {document_id} not found")
            return {
                "success": False,
                "message": f"Document with ID {document_id} not found",
                "content": None,
                "file_name": None,
            }

        # Return document content
        return {
            "success": True,
            "message": "Document content retrieved successfully",
            "content": document.get("content", ""),
            "file_name": document.get("file_name", "Unknown"),
            "document_id": document_id,
        }

    except ConnectionFailure as e:
        error_msg = f"Failed to connect to MongoDB: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "content": None,
            "file_name": None,
        }

    except OperationFailure as e:
        error_msg = f"MongoDB operation failed: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "content": None,
            "file_name": None,
        }

    except Exception as e:
        error_msg = f"Error retrieving document: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "content": None,
            "file_name": None,
        }
