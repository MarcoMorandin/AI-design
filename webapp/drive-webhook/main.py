import datetime
import uuid
import json
import uvicorn
from fastapi import FastAPI, HTTPException, Header  # Removed Request
from pymongo import MongoClient
from googleapiclient.errors import HttpError
import logging

# --- Configuration ---
from config import (
    PORT,  # Changed from FLASK_PORT_WATCHER
    WATCHER_SERVICE_PUBLIC_URL,
    MONGO_URI,
    MONGO_DB_NAME,
)
from utils import (
    get_google_credentials_from_db,
    get_google_drive_service,
)  # Changed from .utils
from file_processor import process_new_file  # Changed from .file_processor


# --- Helper function for hierarchy check ---
def is_file_in_hierarchy(
    drive_service,
    file_item_parents,
    target_ancestor_folder_id,
    logger_instance,
    max_depth=7,
):
    """
    Checks if a file (given its parent IDs) is a descendant of target_ancestor_folder_id.
    """
    if not file_item_parents:
        return False  # File is in "My Drive" root or a shared drive root

    if target_ancestor_folder_id in file_item_parents:
        return True  # File is a direct child of the target folder

    current_parents_to_check = list(file_item_parents)
    visited_folders = set(file_item_parents)

    for _ in range(max_depth):  # Limit recursion depth to prevent excessive API calls
        if not current_parents_to_check:
            break

        next_level_parents = []
        parent_ids_for_this_level = list(
            current_parents_to_check
        )  # Iterate over a copy
        current_parents_to_check = []  # Reset for next iteration

        for parent_id in parent_ids_for_this_level:
            if (
                parent_id == target_ancestor_folder_id
            ):  # Should be caught by the initial check if direct parent
                return True  # Should not happen here if initial check is done.
            try:
                # logger_instance.debug(f"Hierarchy check: Fetching parents of {parent_id}")
                parent_meta = (
                    drive_service.files()
                    .get(
                        fileId=parent_id,
                        fields="id, name, parents",  # Added name for logging if needed
                        supportsAllDrives=True,
                    )
                    .execute()
                )

                grand_parents = parent_meta.get("parents", [])
                if target_ancestor_folder_id in grand_parents:
                    return True  # File's grandparent (or higher ancestor) is the target

                for gp_id in grand_parents:
                    if gp_id not in visited_folders:
                        next_level_parents.append(gp_id)
                        visited_folders.add(gp_id)
            except HttpError as e:
                # If a 404 happens, it might mean the parent folder was deleted or permissions changed.
                # If it's a permission error, we might not be able to traverse up this path.
                logger_instance.warning(
                    f"HttpError (status: {e.resp.status if hasattr(e, 'resp') else 'N/A'}) getting parent {parent_id} for hierarchy check: {e}"
                )
            except Exception as e:
                logger_instance.error(
                    f"Unexpected error getting parent {parent_id} for hierarchy check: {e}",
                    exc_info=True,
                )

        current_parents_to_check.extend(next_level_parents)

    return False


# --- FastAPI App Initialization ---
app = FastAPI()  # Changed from Flask to FastAPI


# --- Health Check Endpoint for Docker ---
@app.get("/health")
async def health_check():
    """Health check endpoint for container monitoring"""
    # Check MongoDB connection
    mongo_status = "OK" if mongo_client else "ERROR"
    return {
        "status": "healthy" if mongo_client else "unhealthy",
        "mongo_connection": mongo_status,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- MongoDB Client Initialization ---
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    users_collection = db["users"]  # This is the collection to be passed
    watch_channels_collection = db["watch_channels"]  # To store active watch channels
    watch_channels_collection.create_index("channelId", unique=True)
    logger.info("Watcher Service: Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"Watcher Service: Error connecting to MongoDB: {e}")
    mongo_client = None  # Ensure these are None if connection fails
    db = None
    users_collection = None
    watch_channels_collection = None


# --- FastAPI Routes ---
@app.post(
    "/watch/folder/{user_google_id}"
)  # Changed to app.post and FastAPI path param syntax
async def initiate_watch(
    user_google_id: str,
):  # Removed request: Request
    """
    Initiates a watch on the user's 'moodleAI' folder in Google Drive.
    """
    user = users_collection.find_one({"googleId": user_google_id})
    if not user or not user.get("driveFolderId"):
        logger.warning(
            f"User or Drive folder not found for Google ID: {user_google_id}"
        )
        raise HTTPException(
            status_code=404, detail="User or Drive folder not found for this Google ID"
        )

    root_folder_id_user_selected = user[
        "driveFolderId"
    ]  # This is the folder user wants to monitor
    credentials = get_google_credentials_from_db(user_google_id, users_collection)
    if not credentials:
        logger.error(
            f"Could not obtain valid Google credentials for user: {user_google_id}"
        )
        raise HTTPException(
            status_code=500, detail="Could not obtain valid Google credentials for user"
        )

    drive_service = get_google_drive_service(credentials)
    if not drive_service:
        logger.error(
            f"Could not create Google Drive service instance for user: {user_google_id}"
        )
        raise HTTPException(
            status_code=500, detail="Could not create Google Drive service instance"
        )

    channel_id = str(uuid.uuid4())
    notification_url = f"{WATCHER_SERVICE_PUBLIC_URL}/notifications/drive"

    watch_request_body = {
        "id": channel_id,
        "type": "web_hook",
        "address": notification_url,
        "params": {"ttl": "86400"},  # TTL is a string
        # token is an optional user-defined string, not used here
    }

    try:
        logger.info(
            f"Attempting to initiate 'changes' watch for user {user_google_id} (monitoring root: {root_folder_id_user_selected})."
        )
        logger.info(f"Notification URL: {notification_url}, Channel ID: {channel_id}")

        # 1. Get the initial start page token FIRST
        logger.info(
            f"Fetching startPageToken for user {user_google_id} before initiating watch."
        )
        token_response = (
            drive_service.changes().getStartPageToken(supportsAllDrives=True).execute()
        )
        start_page_token = token_response.get("startPageToken")
        if not start_page_token:
            logger.error(
                f"Failed to get startPageToken for user {user_google_id}. Cannot initiate watch."
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to get initial startPageToken from Google Drive. Watch not initiated.",
            )
        logger.info(
            f"Obtained startPageToken: {start_page_token} for user {user_google_id}"
        )

        # 2. Use changes.watch with the obtained pageToken
        watch_response = (
            drive_service.changes()
            .watch(
                body=watch_request_body,
                pageToken=start_page_token,  # Pass the token here
                supportsAllDrives=True,
            )
            .execute()
        )

        # The start_page_token is already fetched and validated.
        # No need to fetch it again or handle the orphaned channel scenario related to fetching it after watch.

        channel_info = {
            "channelId": watch_response["id"],
            "resourceId": watch_response[
                "resourceId"
            ],  # Keep resourceId for stopping the channel
            "userGoogleId": user_google_id,
            "rootFolderIdUserSelected": root_folder_id_user_selected,  # Store the user's target folder
            "pageToken": start_page_token,  # Store the initial page token
            "expiration": datetime.datetime.utcnow()
            + datetime.timedelta(milliseconds=int(watch_response["expiration"])),
            "createdAt": datetime.datetime.utcnow(),
        }
        watch_channels_collection.insert_one(channel_info)

        logger.info(
            f"Successfully initiated 'changes' watch for user {user_google_id}. Root folder: {root_folder_id_user_selected}, Channel ID: {watch_response['id']}, Initial PageToken: {start_page_token}"
        )
        return {
            "message": "Changes watch initiated successfully",
            "channelId": watch_response["id"],
            "resourceId": watch_response["resourceId"],
            "expiration": watch_response["expiration"],
        }  # FastAPI returns dicts as JSON

    except HttpError as error:
        error_details = {}
        try:
            error_content = error.content.decode()
            error_details = json.loads(error_content)
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
            error_details = {
                "message": "Failed to decode error content from Google.",
                "original_content": str(error.content),
            }
        logger.error(f"HttpError initiating watch: {error_details}")
        raise HTTPException(
            status_code=(
                error.resp.status
                if hasattr(error, "resp") and hasattr(error.resp, "status")
                else 500
            ),
            detail={
                "error": "Failed to initiate watch on Drive folder",
                "details": error_details,
            },
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred initiating watch: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "An unexpected error occurred", "details": str(e)},
        )


@app.post("/notifications/drive")  # Changed to app.post
async def google_drive_notifications(  # async def
    x_goog_channel_id: str = Header(None),
    x_goog_resource_id: str = Header(None),
    x_goog_resource_state: str = Header(None),
    x_goog_message_number: str = Header(None),
):  # Removed request: Request, Use FastAPI Header for specific headers
    """
    Receives push notifications from Google Drive for changes.
    """

    # --- Enhanced Logging for Incoming Notification ---
    notification_details = {
        "X-Goog-Channel-ID": x_goog_channel_id,
        "X-Goog-Resource-ID": x_goog_resource_id,
        "X-Goog-Resource-State": x_goog_resource_state,
        "X-Goog-Message-Number": x_goog_message_number,
        "X-Goog-Channel-Expiration": Header(
            None, alias="x-goog-channel-expiration"
        ),  # Capture expiration if sent
        "X-Goog-Resource-URI": Header(
            None, alias="x-goog-resource-uri"
        ),  # Capture resource URI if sent
    }
    logger.info(
        f"Received Google Drive notification with headers: {notification_details}"
    )

    # Check if collections are None explicitly
    if users_collection is None or watch_channels_collection is None:
        logger.error(
            "Error: Database collection(s) not available in google_drive_notifications."
        )
        raise HTTPException(
            status_code=500, detail="Internal server error: DB not configured"
        )

    # Headers are now accessed via parameters with Header() default
    channel_id = x_goog_channel_id
    resource_id_header = x_goog_resource_id
    resource_state = x_goog_resource_state
    message_number = x_goog_message_number

    logger.info(
        f"Received notification: Channel={channel_id}, Resource={resource_id_header}, State={resource_state}, MsgNum={message_number}"
    )

    if not channel_id:
        logger.warning("Notification missing X-Goog-Channel-ID header.")
        raise HTTPException(status_code=400, detail="Missing channel ID header")

    active_channel = watch_channels_collection.find_one({"channelId": channel_id})
    if not active_channel:
        logger.warning(f"Notification for unknown or expired channel ID: {channel_id}")
        return {
            "message": "Notification acknowledged for unknown channel"
        }  # FastAPI returns dicts as JSON

    user_google_id = active_channel["userGoogleId"]
    current_page_token = active_channel.get("pageToken")
    root_folder_id_user_selected = active_channel.get("rootFolderIdUserSelected")

    if not current_page_token or not root_folder_id_user_selected:
        logger.error(
            f"Channel {channel_id} is missing pageToken or rootFolderIdUserSelected. DB record: {active_channel}"
        )
        # Potentially stop the channel or mark as invalid
        return {"message": "Notification acknowledged but channel data incomplete"}

    if resource_state == "sync":
        logger.info(
            f"Sync notification for channel {channel_id}. Will check for changes."
        )
        # A 'sync' notification means we should list changes.
        # Other states like 'add', 'remove', 'update', 'trash' might also come,
        # but the reliable way is to always list changes using the pageToken.

    logger.info(
        f"Processing notification for user {user_google_id}, channel {channel_id}, monitored root {root_folder_id_user_selected}. State: {resource_state}. Current PageToken: {current_page_token}"
    )

    credentials = get_google_credentials_from_db(user_google_id, users_collection)
    if not credentials:
        logger.error(
            f"Could not get credentials for user {user_google_id} to process notification."
        )
        raise HTTPException(
            status_code=500,
            detail="Internal error processing notification (credentials)",
        )

    drive_service = get_google_drive_service(credentials)
    if not drive_service:
        logger.error(f"Could not create Drive service for user {user_google_id}.")
        raise HTTPException(
            status_code=500,
            detail="Internal error processing notification (drive service)",
        )

    try:
        page_token_for_request = current_page_token
        processed_changes_count = 0

        while True:  # Loop to handle paginated changes
            logger.info(
                f"Fetching changes for user {user_google_id} with pageToken: {page_token_for_request}"
            )
            changes_response = (
                drive_service.changes()
                .list(
                    pageToken=page_token_for_request,
                    fields="nextPageToken, newStartPageToken, changes(changeType, time, fileId, removed, file(id, name, mimeType, parents, trashed, capabilities, shared, sharingUser, owners, driveId, createdTime, modifiedTime))",  # Added 'time' to changes fields
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageSize=100,  # Adjust as needed
                )
                .execute()
            )

            for change in changes_response.get("changes", []):
                processed_changes_count += 1
                file_id = change.get("fileId")
                is_removed = change.get("removed", False)
                change_type = change.get("changeType")  # e.g., 'file', 'drive'
                change_time = change.get("time")  # Timestamp of the change

                logger.info(
                    f"Processing Change: FileID={file_id}, ChangeType={change_type}, Removed={is_removed}, ChangeTime={change_time}, FullChangeObject={change}"
                )

                if is_removed:
                    logger.info(f"File {file_id} was removed. (User: {user_google_id})")
                    # Add logic here if you need to react to deletions (e.g., remove from your system)
                    # For now, we just log it.
                    continue

                if not change.get("file"):
                    logger.warning(
                        f"Change for fileId {file_id} has no 'file' metadata. Skipping. Change: {change}"
                    )
                    continue

                file_metadata = change.get("file")

                if file_metadata.get("trashed"):
                    logger.info(
                        f"File {file_metadata.get('name')} ({file_id}) is in trash. Skipping."
                    )
                    continue

                if (
                    file_metadata.get("mimeType")
                    == "application/vnd.google-apps.folder"
                ):
                    logger.info(
                        f"Change pertains to a folder: {file_metadata.get('name')} ({file_id}). Skipping direct processing of folder, will process its contents if they change."
                    )
                    continue  # We are interested in file changes, not folder changes themselves unless we want to rescan.

                # Check if the file is within the user's specified root folder hierarchy
                file_parents = file_metadata.get("parents")
                if not file_parents:
                    logger.debug(
                        f"File {file_metadata.get('name')} ({file_id}) has no parents (root of a drive). Checking if it IS the root watched folder."
                    )
                    if (
                        file_id == root_folder_id_user_selected
                        and file_metadata.get("mimeType")
                        != "application/vnd.google-apps.folder"
                    ):
                        logger.info(
                            f"File {file_metadata.get('name')} ({file_id}) is the root watched item (and is a file). Processing."
                        )
                        process_new_file(
                            file_metadata,
                            user_google_id,
                            root_folder_id_user_selected,  # Pass the root folder context
                            drive_service=drive_service,
                        )
                    else:
                        logger.info(
                            f"File {file_metadata.get('name')} ({file_id}) is in a drive root but not the specified watched folder or is a folder. Skipping."
                        )
                    continue

                logger.debug(
                    f"Checking hierarchy for file: {file_metadata.get('name')} ({file_id}), parents: {file_parents}, target root: {root_folder_id_user_selected}"
                )
                if is_file_in_hierarchy(
                    drive_service, file_parents, root_folder_id_user_selected, logger
                ):
                    logger.info(
                        f"File {file_metadata.get('name')} ({file_id}) is within the watched hierarchy of {root_folder_id_user_selected}. Processing."
                    )
                    process_new_file(
                        file_metadata,
                        user_google_id,
                        root_folder_id_user_selected,  # Pass the root folder context
                        drive_service=drive_service,
                    )
                else:
                    logger.info(
                        f"File {file_metadata.get('name')} ({file_id}) is NOT in the watched hierarchy of {root_folder_id_user_selected}. Skipping."
                    )

            next_page_token_from_response = changes_response.get("nextPageToken")
            if next_page_token_from_response:
                page_token_for_request = next_page_token_from_response
            else:
                # No more pages in this batch of changes
                break

        logger.info(
            f"Processed {processed_changes_count} change(s) for user {user_google_id}."
        )

        # Update the page token in the database for the next notification
        # newStartPageToken should be used if present, as it indicates the token for future polling if the old one expires.
        # Otherwise, use the nextPageToken from the last page of current changes (which would be None if all changes fit one page).
        # If nextPageToken is None after looping, it means we've processed all current changes up to this point.
        # The token to store for the *next* notification is the newStartPageToken if available,
        # or the nextPageToken from the *last* successful changes.list() call if newStartPageToken isn't there.
        # If both are null, it means we are at the latest state, and the current_page_token is still valid for the next notification.

        final_token_to_store = changes_response.get("newStartPageToken")
        if not final_token_to_store:
            # If newStartPageToken is not available, it means the old pageToken is still valid for the next poll.
            # However, if we paged through results, page_token_for_request would be the last nextPageToken.
            # If there were no more pages (next_page_token_from_response was None),
            # then the original current_page_token effectively represents the "end" of this change set.
            # The Google Drive API documentation suggests that if newStartPageToken is not present,
            # the pageToken from the initial changes.watch or the last changes.list (if paginated)
            # should be used for the next poll.
            # If page_token_for_request was updated to a nextPageToken, that's the one to save.
            # If it was the initial current_page_token and no nextPageToken came, that one is still fine.
            final_token_to_store = page_token_for_request  # This will be the last nextPageToken or the initial token if no pagination

        if final_token_to_store and final_token_to_store != current_page_token:
            watch_channels_collection.update_one(
                {"channelId": channel_id}, {"$set": {"pageToken": final_token_to_store}}
            )
            logger.info(
                f"Updated pageToken for channel {channel_id} to {final_token_to_store}"
            )
        elif not final_token_to_store:
            logger.warning(
                f"No new pageToken (newStartPageToken or nextPageToken) received for channel {channel_id}. Original token {current_page_token} remains."
            )
        else:  # final_token_to_store == current_page_token
            logger.info(
                f"PageToken for channel {channel_id} ({current_page_token}) remains unchanged as no new token was provided by the API."
            )

    except HttpError as error:
        logger.error(
            f"HttpError processing notification for user {user_google_id}: {error}"
        )
        raise HTTPException(status_code=500, detail="Failed to process Drive changes")
    except Exception as e:
        logger.error(f"Unexpected error processing notification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unexpected error during notification processing",
        )

    return {"message": "Notification received and acknowledged"}


@app.post("/stop-watch/{channel_id_to_stop}")  # Changed to app.post
async def stop_watch_channel(
    channel_id_to_stop: str,
):  # Removed request: Request, async def, type hint
    """Stops an active watch channel."""
    if not all([users_collection, watch_channels_collection]):
        logger.error(
            "Database not configured or connection failed in stop_watch_channel"
        )
        raise HTTPException(
            status_code=500, detail="Database not configured or connection failed"
        )

    channel_doc = watch_channels_collection.find_one({"channelId": channel_id_to_stop})
    if not channel_doc:
        logger.warning(
            f"Channel not found for ID: {channel_id_to_stop} during stop operation."
        )
        raise HTTPException(status_code=404, detail="Channel not found")

    user_google_id = channel_doc["userGoogleId"]
    resource_id = channel_doc["resourceId"]

    credentials = get_google_credentials_from_db(user_google_id, users_collection)
    if not credentials:
        logger.error(
            f"Could not obtain valid Google credentials for user: {user_google_id} during stop operation."
        )
        raise HTTPException(
            status_code=500, detail="Could not obtain valid Google credentials for user"
        )

    drive_service = get_google_drive_service(credentials)
    if not drive_service:
        logger.error(
            f"Could not create Google Drive service instance for user: {user_google_id} during stop operation."
        )
        raise HTTPException(
            status_code=500, detail="Could not create Google Drive service instance"
        )

    try:
        drive_service.channels().stop(
            body={"id": channel_id_to_stop, "resourceId": resource_id}
        ).execute()
        watch_channels_collection.delete_one({"channelId": channel_id_to_stop})
        logger.info(f"Successfully stopped watch channel: {channel_id_to_stop}")
        return {
            "message": f"Channel {channel_id_to_stop} stopped."
        }  # FastAPI returns dicts as JSON
    except HttpError as error:
        logger.error(f"Error stopping channel {channel_id_to_stop}: {error}")
        if hasattr(error, "resp") and error.resp.status == 404:
            # If Google says not found, it might have expired or been stopped already.
            # We should remove it from our DB to keep things clean.
            logger.warning(
                f"Channel {channel_id_to_stop} not found on Google's side, removing from DB."
            )
            watch_channels_collection.delete_one({"channelId": channel_id_to_stop})
            # Return a success-like response as the desired state (channel stopped) is achieved.
            return {
                "message": "Channel not found on Google's side (already stopped/expired?), removed from DB."
            }
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to stop channel", "details": str(error)},
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred stopping watch: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "An unexpected error occurred", "details": str(e)},
        )


if __name__ == "__main__":
    
    logger.info(f"Watcher service (FastAPI) running on http://localhost:{PORT}")
    logger.info(
        f"Ensure your public notification URL '{WATCHER_SERVICE_PUBLIC_URL}/notifications/drive' is accessible."
    )
    # Use uvicorn to run the app
    import os

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
    )
