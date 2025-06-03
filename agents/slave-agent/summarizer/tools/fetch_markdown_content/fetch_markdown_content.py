from typing import Dict, Any
import logging
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Add the parent directory to the path to import utils
sys.path.append(os.path.dirname(__file__) + "/..")
from utils import sanitize_content

load_dotenv()
logger = logging.getLogger(__name__)

# Get database configuration from environment
DB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "markdown_documents")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION", "documents")


async def fetch_markdown_content(document_id: str) -> Dict[str, Any]:
    """
    Retrieves markdown content from the database using the Google Document ID.

    Args:
        document_id: The Google Document ID of the document to retrieve from the database

    Returns:
        Dict containing the markdown content and metadata

    Tool:
        name: fetch_markdown_content
        description: Retrieves markdown content from the database using the Google Document ID
        input_schema:
            type: object
            properties:
                document_id:
                    type: string
                    description: The Google Document ID of the document to retrieve from the database
            required:
                - document_id
        output_schema:
            type: object
            properties:
                content:
                    type: string
                    description: The markdown content of the document
                title:
                    type: string
                    description: The title of the document
                metadata:
                    type: object
                    description: Additional metadata about the document
                success:
                    type: boolean
                    description: Whether the operation was successful
                message:
                    type: string
                    description: Status message or error information
    """
    try:
        logger.info(f"Fetching document with Google Document ID: {document_id}")

        # Connect to MongoDB
        client = MongoClient(DB_URI, serverSelectionTimeoutMS=5000)

        # Select database and collection
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Query for the document using google_document_id field
        document = collection.find_one({"google_document_id": document_id})

        # Close the connection
        client.close()

        if not document:
            logger.warning(
                f"Document with Google Document ID {document_id} not found in database"
            )
            return {
                "success": False,
                "message": f"Document with Google Document ID {document_id} not found",
                "content": "",
                "title": "",
                "metadata": {},
            }

        # Extract content and metadata
        content = document.get("content", "")
        title = document.get("title", "Untitled Document")
        
        # Sanitize content to remove invalid control characters
        if content:
            content = sanitize_content(content)
        
        # Validate that content is not empty after sanitization
        if not content:
            logger.warning(f"Document {document_id} exists but has no content after sanitization")
            return {
                "success": False,
                "message": f"Document {document_id} exists but contains no valid content",
                "content": "",
                "title": title,
                "metadata": {},
            }
        
        metadata = {
            "author": document.get("author", "Unknown"),
            "created_at": document.get("created_at", ""),
            "updated_at": document.get("updated_at", ""),
            "tags": document.get("tags", []),
        }

        logger.info(f"Successfully retrieved document: {title}")

        return {
            "success": True,
            "message": f"Document retrieved successfully. Size: {len(content)} characters. Ready for chunking.",
            "content": content,
            "title": title,
            "metadata": metadata,
        }

    except ConnectionFailure as e:
        logger.error(f"Database connection error: {str(e)}")
        return {
            "success": False,
            "message": f"Database connection error: {str(e)}",
            "content": "",
            "title": "",
            "metadata": {},
        }
    except OperationFailure as e:
        logger.error(f"Database operation failed: {str(e)}")
        return {
            "success": False,
            "message": f"Database operation failed: {str(e)}",
            "content": "",
            "title": "",
            "metadata": {},
        }
    except Exception as e:
        logger.error(f"Error fetching document: {str(e)}")
        return {
            "success": False,
            "message": f"Error fetching document: {str(e)}",
            "content": "",
            "title": "",
            "metadata": {},
        }
