import os
import json  # Add import for JSON handling
from typing import Dict, Any, List
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


async def reorganize_drive(
    proposed_structure: Dict[str, Any], user_data: Dict[str, Any], folder_id: str
) -> Dict[str, Any]:
    """Implements the proposed folder structure in Google Drive.
    Creates folders and moves files according to the proposed organization.

    Args:
        proposed_structure: Proposed folder structure with file assignments
        user_data: User data containing Google credentials
        folder_id: The Google Drive folder ID to reorganize

    Returns:
        Dict containing success status, message, and lists of created folders and moved files

    Tool:
        name: reorganize_drive
        description: Implements the proposed folder structure in Google Drive
        input_schema:
            type: object
            properties:
                proposed_structure:
                    type: object
                    description: Proposed folder structure with file assignments
                user_data:
                    type: object
                    description: User data containing Google credentials
                folder_id:
                    type: string
                    description: The Google Drive folder ID to reorganize
            required:
                - proposed_structure
                - user_data
                - folder_id
        output_schema:
            type: object
            properties:
                success:
                    type: boolean
                    description: Whether the reorganization was successful
                message:
                    type: string
                    description: Status message
                created_folders:
                    type: array
                    description: List of folders that were created
                moved_files:
                    type: array
                    description: List of files that were moved
    """
    try:
        logger.info(f"Reorganizing Google Drive folder: {folder_id}")

        # Handle proposed_structure as string if it's not already a dictionary
        if isinstance(proposed_structure, str):
            try:
                proposed_structure = json.loads(proposed_structure)
                logger.debug("Converted proposed_structure from string to dictionary")
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Invalid proposed_structure format: not a valid JSON string",
                    "created_folders": [],
                    "moved_files": [],
                }

        # Handle user_data as string if it's not already a dictionary
        if isinstance(user_data, str):
            try:
                user_data = json.loads(user_data)
                logger.debug("Converted user_data from string to dictionary")
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Invalid user_data format: not a valid JSON string",
                    "created_folders": [],
                    "moved_files": [],
                }

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

        created_folders = []
        moved_files = []

        # Create new folders based on proposed structure
        folder_id_mapping = (
            {}
        )  # Maps our temporary IDs to actual Google Drive folder IDs

        for subfolder in proposed_structure.get("root", {}).get("subfolders", []):
            folder_name = subfolder.get("name")
            temp_folder_id = subfolder.get("id")

            # Create the folder in Google Drive
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [folder_id],
            }

            created_folder = (
                drive_service.files()
                .create(body=folder_metadata, fields="id, name")
                .execute()
            )

            real_folder_id = created_folder.get("id")
            folder_id_mapping[temp_folder_id] = real_folder_id

            created_folders.append({"name": folder_name, "id": real_folder_id})

            logger.info(f"Created folder: {folder_name} with ID: {real_folder_id}")

        # Move files to their assigned folders
        for subfolder in proposed_structure.get("root", {}).get("subfolders", []):
            temp_folder_id = subfolder.get("id")
            real_folder_id = folder_id_mapping.get(temp_folder_id)

            for file in subfolder.get("files", []):
                file_id = file.get("file_id")
                file_name = file.get("file_name")

                try:
                    # Move the file to the new folder
                    drive_service.files().update(
                        fileId=file_id,
                        addParents=real_folder_id,
                        removeParents=folder_id,
                        fields="id, name, parents",
                    ).execute()

                    moved_files.append(
                        {
                            "name": file_name,
                            "id": file_id,
                            "destination_folder": subfolder.get("name"),
                        }
                    )

                    logger.info(
                        f"Moved file: {file_name} to folder: {subfolder.get('name')}"
                    )

                except HttpError as error:
                    logger.error(f"Error moving file {file_name}: {str(error)}")
                    # Continue with other files even if one fails

        # Generate summary message
        summary = f"Reorganization complete. Created {len(created_folders)} folders and moved {len(moved_files)} files."

        logger.info(summary)
        return {
            "success": True,
            "message": summary,
            "created_folders": created_folders,
            "moved_files": moved_files,
        }

    except Exception as e:
        logger.error(f"Error reorganizing Drive: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error reorganizing Drive: {str(e)}",
            "created_folders": [],
            "moved_files": [],
        }
