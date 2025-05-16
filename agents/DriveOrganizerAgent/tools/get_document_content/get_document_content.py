import os
import tempfile
from typing import Dict, Any
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
import io
from pymongo import MongoClient
import json

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()
# MongoDB connection settings from environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ai-design")


async def get_document_content(
    file_id: str, user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Retrieves the content of a document from Google Drive file ID.
    First checks MongoDB if the file has already been processed and stored.
    If not found in MongoDB, attempts to extract text from the file via Google Drive.

    Args:
        file_id: The Google Drive file ID
        user_data: User data containing Google credentials

    Returns:
        Dict containing document content, metadata, and status

    Tool:
        name: get_document_content
        description: Retrieves the content of a document from Google Drive or MongoDB
        input_schema:
            type: object
            properties:
                file_id:
                    type: string
                    description: The Google Drive file ID
                user_data:
                    type: object
                    description: User data containing Google credentials
            required:
                - file_id
                - user_data
        output_schema:
            type: object
            properties:
                content:
                    type: string
                    description: The text content of the document
                file_name:
                    type: string
                    description: The name of the file
                mime_type:
                    type: string
                    description: The MIME type of the file
                success:
                    type: boolean
                    description: Whether the operation was successful
                message:
                    type: string
                    description: Status message
                file_id:
                    type: string
                    description: The Google Drive file ID
    """
    try:
        logger.info(f"Retrieving document content for file ID: {file_id}")

        # Handle user_data as string if it's not already a dictionary
        if isinstance(user_data, str):
            try:
                user_data = json.loads(user_data)
                logger.debug("Converted user_data from string to dictionary")
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Invalid user_data format: not a valid JSON string",
                    "content": "",
                    "mime_type": "",
                }

        # First check if document content exists in MongoDB
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        documents_collection = db["documents"]

        existing_doc = documents_collection.find_one({"fileId": file_id})

        if existing_doc and "content" in existing_doc:
            logger.info(f"Document content found in MongoDB for file ID: {file_id}")
            client.close()
            return {
                "success": True,
                "message": "Document content retrieved from MongoDB",
                "content": existing_doc["content"],
                "file_name": existing_doc.get("fileName", "Unknown"),
                "mime_type": existing_doc.get("mimeType", "Unknown"),
                "file_id": file_id,
            }

        client.close()
    except Exception as e:
        logger.error(f"Error retrieving document content: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error retrieving document content: {str(e)}",
            "content": "",
            "file_name": "",
            "mime_type": "",
        }
