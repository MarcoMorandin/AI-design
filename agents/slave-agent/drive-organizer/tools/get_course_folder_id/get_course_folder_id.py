import os
import json
from typing import Dict, Any
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from dotenv import load_dotenv

# Import shared Google auth utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from google_auth_utils import create_and_refresh_credentials

load_dotenv()
logger = logging.getLogger(__name__)


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

        # Log the exact type and content of user_data for debugging
        logger.warning(f"Received user_data of type: {type(user_data)}")
        logger.warning(f"User_data content (first 500 chars): {repr(str(user_data)[:500])}")

        # Handle different possible formats of user_data input
        if isinstance(user_data, str):
            logger.warning(f"Received user_data as string: '{user_data[:100]}...'")
            try:
                parsed_data = json.loads(user_data)
                # Check if this is the full response from retrieve_user_data
                if isinstance(parsed_data, dict) and "user_data" in parsed_data:
                    logger.info("Detected full retrieve_user_data response, extracting user_data field")
                    user_data = parsed_data["user_data"]
                else:
                    user_data = parsed_data
                logger.debug("Converted user_data from string to dictionary")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse user_data JSON: {e}")
                logger.error(f"Raw user_data received: {repr(user_data)}")
                return {
                    "success": False,
                    "message": f"Invalid user_data format: not a valid JSON string. Received type: {type(user_data)}, Content: {repr(str(user_data)[:200])}",
                    "folder_id": "",
                }
        elif isinstance(user_data, dict):
            # Check if this is the full response from retrieve_user_data
            if "user_data" in user_data and "success" in user_data:
                logger.info("Detected full retrieve_user_data response as dict, extracting user_data field")
                user_data = user_data["user_data"]
        elif not isinstance(user_data, dict):
            logger.error(f"user_data is not a string or dict, it's: {type(user_data)}")
            logger.error(f"user_data content: {repr(user_data)}")
            return {
                "success": False,
                "message": f"Invalid user_data format: expected dict or JSON string, got {type(user_data)}. Content: {repr(str(user_data)[:200])}",
                "folder_id": "",
            }
        
        # Validate that we now have a proper user_data dict
        if not isinstance(user_data, dict):
            logger.error(f"After processing, user_data is still not a dict: {type(user_data)}")
            return {
                "success": False,
                "message": f"Could not extract valid user_data dictionary. Final type: {type(user_data)}",
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
            
            # Create credentials object with refresh
            credentials = create_and_refresh_credentials(google_tokens)

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

        # Create credentials object with refresh
        credentials = create_and_refresh_credentials(google_tokens)

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

    except RefreshError as refresh_error:
        logger.error(f"Google OAuth refresh error: {str(refresh_error)}", exc_info=True)
        return {
            "success": False,
            "message": f"Google OAuth credentials expired and refresh failed: {str(refresh_error)}. User needs to re-authenticate.",
            "folder_id": "",
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
