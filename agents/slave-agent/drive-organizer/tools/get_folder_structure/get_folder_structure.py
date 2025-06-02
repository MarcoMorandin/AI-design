from typing import Dict, Any, List
import logging
import os
import sys
import json 
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from dotenv import load_dotenv

# Import shared Google auth utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from google_auth_utils import create_and_refresh_credentials

logger = logging.getLogger(__name__)

load_dotenv()


async def get_folder_structure(
    folder_id: str, user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Retrieves the structure of a Google Drive folder, including all files and subfolders.
    Uses the user's Google Drive credentials from the user_data object.

    Args:
        folder_id: The Google Drive folder ID
        user_data: User data containing Google credentials

    Returns:
        Dict containing folder structure, success status and message

    Tool:
        name: get_folder_structure
        description: Retrieves the folder structure from Google Drive using the folder ID and user credentials
        input_schema:
            type: object
            properties:
                folder_id:
                    type: string
                    description: The Google Drive folder ID
                user_data:
                    type: object
                    description: User data containing Google credentials
            required:
                - folder_id
                - user_data
        output_schema:
            type: object
            properties:
                folder_structure:
                    type: array
                    description: List of files and folders in the specified location
                success:
                    type: boolean
                    description: Whether the operation was successful
                message:
                    type: string
                    description: Status message
    """
    try:
        logger.info(f"Retrieving folder structure for folder ID: {folder_id}")

        # Handle user_data as string if it's not already a dictionary
        if isinstance(user_data, str):
            try:
                user_data = json.loads(user_data)
                logger.debug("Converted user_data from string to dictionary")
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Invalid user_data format: not a valid JSON string",
                    "folder_structure": [],
                }

        # Extract Google credentials from user data
        google_tokens = user_data.get("googleTokens", {})

        # Create credentials object with refresh
        credentials = create_and_refresh_credentials(google_tokens)

        # Build the Drive service
        drive_service = build("drive", "v3", credentials=credentials)

        # Query to get all files and folders in the given folder
        query = f"'{folder_id}' in parents and trashed=false"

        # Get the list of files and folders
        results = (
            drive_service.files()
            .list(
                q=query,
                fields="files(id, name, mimeType, createdTime, modifiedTime)",
                pageSize=1000,
            )
            .execute()
        )

        items = results.get("files", [])

        # Categorize items into files and folders
        folder_structure = []
        for item in items:
            item_type = (
                "folder"
                if item["mimeType"] == "application/vnd.google-apps.folder"
                else "file"
            )
            folder_structure.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "type": item_type,
                    "mimeType": item["mimeType"],
                    "createdTime": item["createdTime"],
                    "modifiedTime": item["modifiedTime"],
                }
            )

        logger.info(
            f"Successfully retrieved folder structure with {len(folder_structure)} items"
        )
        return {
            "success": True,
            "message": f"Retrieved {len(folder_structure)} items from folder",
            "folder_structure": folder_structure,
        }

    except HttpError as error:
        logger.error(f"Google Drive API error: {str(error)}", exc_info=True)
        return {
            "success": False,
            "message": f"Google Drive API error: {str(error)}",
            "folder_structure": [],
        }
    except Exception as e:
        logger.error(f"Error retrieving folder structure: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error retrieving folder structure: {str(e)}",
            "folder_structure": [],
        }
