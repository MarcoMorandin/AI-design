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
            }

        client.close()

        # If not in MongoDB, get from Google Drive
        # Extract Google credentials from user data
        google_tokens = user_data.get("googleTokens", {})

        # Create credentials object
        credentials = Credentials(
            token=google_tokens.get("access_token"),
            refresh_token=google_tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        # Build the Drive service
        drive_service = build("drive", "v3", credentials=credentials)

        # Get file metadata
        file_metadata = (
            drive_service.files().get(fileId=file_id, fields="name,mimeType").execute()
        )
        file_name = file_metadata.get("name", "Unknown")
        mime_type = file_metadata.get("mimeType", "Unknown")

        content = ""

        # Handle different Google Docs types
        if mime_type == "application/vnd.google-apps.document":
            # Export as plain text for Google Docs
            request = drive_service.files().export_media(
                fileId=file_id, mimeType="text/plain"
            )
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            content = fh.getvalue().decode("utf-8")

        elif mime_type == "application/vnd.google-apps.spreadsheet":
            # Export as CSV for Google Sheets
            request = drive_service.files().export_media(
                fileId=file_id, mimeType="text/csv"
            )
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            content = fh.getvalue().decode("utf-8")

        elif mime_type == "application/vnd.google-apps.presentation":
            # Export as text for Google Slides (limited support)
            request = drive_service.files().export_media(
                fileId=file_id, mimeType="text/plain"
            )
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            content = fh.getvalue().decode("utf-8")

        elif mime_type == "application/pdf":
            # For PDFs, we need more specialized processing
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()

            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                temp_pdf.write(fh.getvalue())
                temp_path = temp_pdf.name

            # Use simple PyPDF2 to extract text (install if needed)
            try:
                from PyPDF2 import PdfReader

                reader = PdfReader(temp_path)
                content = ""
                for page_num in range(len(reader.pages)):
                    content += reader.pages[page_num].extract_text() + "\n"
            except ImportError:
                content = "PDF content extraction not available. PyPDF2 library not installed."
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        # For text files, just get the content directly
        elif mime_type == "text/plain":
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            content = fh.getvalue().decode("utf-8")

        else:
            content = f"Content extraction not supported for MIME type: {mime_type}"

        # Store the document content in MongoDB for future use
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        documents_collection = db["documents"]

        documents_collection.update_one(
            {"fileId": file_id},
            {
                "$set": {
                    "fileId": file_id,
                    "fileName": file_name,
                    "mimeType": mime_type,
                    "content": content,
                    "userId": user_data.get("googleId"),
                }
            },
            upsert=True,
        )

        client.close()

        logger.info(f"Successfully retrieved document content for file: {file_name}")
        return {
            "success": True,
            "message": "Document content retrieved successfully",
            "content": content,
            "file_name": file_name,
            "mime_type": mime_type,
        }

    except Exception as e:
        logger.error(f"Error retrieving document content: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error retrieving document content: {str(e)}",
            "content": "",
            "file_name": "",
            "mime_type": "",
        }
