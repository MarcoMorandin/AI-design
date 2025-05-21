import os
from dotenv import load_dotenv
import logging
from pymongo import MongoClient
from .uplad_in_db import UploadInfo
load_dotenv()

logger = logging.getLogger(__name__)

# MongoDB connection setup
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")
COLLECTION_NAME = "processed_files"
upload_in_vector_db = UploadInfo()


def getText(google_drive_id):
    """
    Retrieves extracted text from MongoDB based on a Google Drive ID.
    If the text isn't found in the database, returns an error message.

    Args:
        google_drive_id (str): The Google Drive ID of the document

    Returns:
        str: The extracted text content from the document or an error message
    """

    # Initialize MongoDB client
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client[MONGO_DB_NAME]
        processed_files_collection = db[COLLECTION_NAME]
        logger.info(f"Connected to MongoDB: {MONGO_DB_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
        mongo_client = None
        db = None
        processed_files_collection = None

        if processed_files_collection is None:
            error_msg = "MongoDB connection is not available"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    try:
        # Query MongoDB for the document with the given Google Drive ID
        document = processed_files_collection.find_one(
            {"google_document_id": google_drive_id}
        )

        # If document is found, return its content
        if document and "content" in document:
            logger.info(
                f"Successfully retrieved content for Google Drive ID: {google_drive_id}"
            )

            upload_in_vector_db.upload_in_kb(document["content"])

            return document["content"]
        else:
            error_msg = f"Document with Google Drive ID {google_drive_id} not found or has no content"
            logger.warning(error_msg)
            return f"Error: {error_msg}"

    except Exception as e:
        error_msg = f"Error retrieving document from MongoDB: {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"
