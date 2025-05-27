import os
import json
from typing import Dict, Any
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)
from dotenv import load_dotenv

load_dotenv()


async def get_course_folder_id(
    user_data: Dict[str, Any], course_name: str
) -> Dict[str, Any]:
    """Find the folder ID for a given course name in the user's Google Drive.
    First retrieves the user's main folder, then searches for a subfolder with the matching name.

    Args:
        user_data: User data containing Google credentials
        course_name: The name of the course to find

    Returns:
        Dict containing folder_id, success status and message

    Tool:
        name: get_course_folder_id
        description: Finds the folder ID for a course by name in the user's Google Drive
        input_schema:
            type: object
            properties:
                user_data:
                    type: object
                    description: User data containing Google credentials
                course_name:
                    type: string
                    description: The name of the course to find
            required:
                - user_data
                - course_name
        output_schema:
            type: object
            properties:
                folder_id:
                    type: string
                    description: The Google Drive folder ID for the course
                success:
                    type: boolean
                    description: Whether the operation was successful
                message:
                    type: string
                    description: Status or error message
    """
    try:
        logger.info(f"Looking for course folder: '{course_name}'")

        # Handle user_data as string if it's not already a dictionary
        if isinstance(user_data, str):
            try:
                user_data = json.loads(user_data)
                logger.debug("Converted user_data from string to dictionary")
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Invalid user_data format: not a valid JSON string",
                    "folder_id": "",
                }

        # Extract Google credentials from user data
        google_tokens = user_data.get("googleTokens", {})
        
        # Try multiple possible field names for the root folder ID
        root_folder_id = user_data.get("rootDriveFolderId") or \
                         user_data.get("rootFolderId") or \
                         user_data.get("driveFolderId") or \
                         user_data.get("driveRootId")
        
        # Log user data structure for debugging (omit sensitive info)
        logger.debug(f"User data keys: {list(user_data.keys())}")
        
        if not root_folder_id:
            # If no root folder ID is found, try to search in all user's folders 
            # or create a new root folder
            logger.warning(f"No root folder ID found for user {user_data.get('googleId', 'unknown')}")
            
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
            
            # Search for a folder with the exact course name at the root level
            # This could be used as a fallback when we don't have a root folder ID
            query = f"name='{course_name}' and mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
            
            results = (
                drive_service.files()
                .list(
                    q=query,
                    fields="files(id, name)",
                    pageSize=10,
                )
                .execute()
            )

            folders = results.get("files", [])
            
            if folders:
                folder_id = folders[0]["id"]
                logger.info(f"Found course folder '{course_name}' at root level: {folder_id}")
                return {
                    "success": True,
                    "message": f"Found folder for course '{course_name}' at root level",
                    "folder_id": folder_id,
                }
            else:
                return {
                    "success": False,
                    "message": "User does not have an associated root folder and course folder not found at root level",
                    "folder_id": "",
                }

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

        # Query to find subfolders in the user's root folder
        query = f"'{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and name='{course_name}' and trashed=false"

        # Search for the course folder
        results = (
            drive_service.files()
            .list(
                q=query,
                fields="files(id, name)",
                pageSize=10,
            )
            .execute()
        )

        folders = results.get("files", [])

        if not folders:
            return {
                "success": False,
                "message": f"Course folder '{course_name}' not found",
                "folder_id": "",
            }

        # Use the first matching folder (should typically be only one)
        folder_id = folders[0]["id"]
        logger.info(f"Found folder for course '{course_name}': {folder_id}")

        return {
            "success": True,
            "message": f"Found folder for course '{course_name}'",
            "folder_id": folder_id,
        }

    except HttpError as error:
        logger.error(f"Google Drive API error: {str(error)}", exc_info=True)
        return {
            "success": False,
            "message": f"Google Drive API error: {str(error)}",
            "folder_id": "",
        }
    except Exception as e:
        logger.error(f"Error finding course folder: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error finding course folder: {str(e)}",
            "folder_id": "",
        }
