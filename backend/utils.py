from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict, Any, Optional
import os

# --- Helper Functions for Google Drive ---
def get_google_drive_service(credentials_dict):  # Renamed parameter for clarity
    """Builds and returns a Google Drive service object."""
    # Add defaults for fields that might be missing when loading from database
    from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    
    # Log a warning if credentials_dict is None or not a dictionary
    if not credentials_dict or not isinstance(credentials_dict, dict):
        print(f"WARNING: Invalid credentials_dict provided: {type(credentials_dict)}")
        return None
    
    # Debug: Print credential keys (without sensitive values)
    print(f"Credential keys available: {list(credentials_dict.keys())}")
    
    # Handle string scope or list of scopes
    scopes = credentials_dict.get("scopes", credentials_dict.get("scope", ""))
    if isinstance(scopes, str) and scopes:
        scopes = scopes.split(" ")
    elif not scopes:
        # Default scopes if none provided
        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        print(f"No scopes found in credentials, using default: {scopes}")
    
    # Construct Credentials object using values with fallbacks
    try:
        creds = Credentials(
            token=credentials_dict.get("access_token"),
            refresh_token=credentials_dict.get("refresh_token"),
            token_uri=credentials_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=credentials_dict.get("client_id", GOOGLE_CLIENT_ID),
            client_secret=credentials_dict.get("client_secret", GOOGLE_CLIENT_SECRET),
            scopes=scopes,
        )
        # The googleapiclient will handle token refresh if the Credentials object is properly configured
        # with a refresh_token and token_uri.
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"Error creating Google Drive service: {e}")
        return None


def create_drive_folder_if_not_exists(drive_service, folder_name):
    """Creates a folder in Google Drive if it doesn't already exist."""
    try:
        # Check if folder already exists
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        response = (
            drive_service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        existing_folders = response.get("files", [])

        if existing_folders:
            print(
                f"Folder '{folder_name}' already exists with ID: {existing_folders[0]['id']}"
            )
            return existing_folders[0]["id"]

        # Create folder if it doesn't exist
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = (
            drive_service.files().create(body=folder_metadata, fields="id").execute()
        )
        print(f"Created folder '{folder_name}' with ID: {folder.get('id')}")
        return folder.get("id")
    except HttpError as error:
        print(f"An error occurred while creating/checking folder: {error}")
        # Handle specific errors, e.g., permission issues
        if error.resp.status == 401:
            print(
                "The credentials have expired or are invalid. Please re-authenticate."
            )
        # Potentially raise the error or return None
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def get_folder_structure(drive_service, folder_id: str) -> List[Dict[str, Any]]:
    """Gets the structure of a folder in Google Drive."""
    try:
        # List all files and folders in the specified folder
        query = f"'{folder_id}' in parents and trashed=false"
        response = (
            drive_service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name, mimeType)",
                pageSize=100,
            )
            .execute()
        )
        
        items = []
        for item in response.get("files", []):
            items.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "mimeType": item.get("mimeType"),
                "isFolder": item.get("mimeType") == "application/vnd.google-apps.folder"
            })
            
        return items
    except HttpError as error:
        print(f"An error occurred retrieving folder structure: {error}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []


def get_hierarchical_folder_structure(drive_service, folder_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
    """Gets the hierarchical structure of a folder in Google Drive up to max_depth levels."""
    def _get_folder_contents(folder_id: str, current_depth: int = 0) -> List[Dict[str, Any]]:
        if current_depth >= max_depth:
            return []
            
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            response = (
                drive_service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="files(id, name, mimeType)",
                    pageSize=100,
                )
                .execute()
            )
            
            items = []
            for item in response.get("files", []):
                item_data = {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "mimeType": item.get("mimeType"),
                    "isFolder": item.get("mimeType") == "application/vnd.google-apps.folder"
                }
                
                # If it's a folder and we haven't reached max depth, get its contents
                if item_data["isFolder"] and current_depth < max_depth - 1:
                    item_data["children"] = _get_folder_contents(item.get("id"), current_depth + 1)
                else:
                    item_data["children"] = []
                    
                items.append(item_data)
                
            return items
        except HttpError as error:
            print(f"An error occurred retrieving folder structure: {error}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return []
    
    return _get_folder_contents(folder_id)


def get_courses(drive_service, user_folder_id: str) -> List[Dict[str, Any]]:
    """Gets the list of courses (top-level subfolders) in the user's folder."""
    try:
        # Only get folders (not files) that are direct children of the user's folder
        query = f"'{user_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = (
            drive_service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        
        courses = []
        for folder in response.get("files", []):
            courses.append({
                "id": folder.get("id"),
                "name": folder.get("name")
            })
            
        return courses
    except HttpError as error:
        print(f"An error occurred retrieving courses: {error}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
        

def get_course_structure(drive_service, course_id: str) -> List[Dict[str, Any]]:
    """Gets the hierarchical structure of a specific course folder (courses > sections > materials)."""
    return get_hierarchical_folder_structure(drive_service, course_id, max_depth=3)


# --- Helper Functions for Orchestrator ---
async def send_message_to_orchestrator(orchestrator_url: str, message: str, user_id: str, 
                                 session_id: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Sends a message to the orchestrator agent using AgentSDK A2AClient and returns the response."""
    try:
        from config import ORCHESTRATOR_URL
        
        # Import A2AClient
        try:
            from trento_agent_sdk.a2a_client import A2AClient
        except ImportError:
            print("AgentSDK not available, please install trento_agent_sdk")
            return {"status": "error", "message": "AgentSDK not available"}
        
        if not orchestrator_url:
            orchestrator_url = ORCHESTRATOR_URL
            
        # Validate that we have a usable orchestrator URL
        if not orchestrator_url or orchestrator_url == "Not set":
            print(f"ERROR: Invalid orchestrator URL: '{orchestrator_url}'")
            return {"status": "error", "message": "Orchestrator URL is not configured properly"}
        
        # Use A2AClient to send the task
        async with A2AClient(orchestrator_url) as client:
            # Send the task with appropriate session_id
            # Note: Let A2AClient generate a unique task_id automatically by not providing one
            # The session_id should be used to group related conversations
            response = await client.send_task(
                message=message,
                task_id=None,  # Let the client generate a unique task ID
                session_id=session_id or str(user_id)  # Use session_id for conversation grouping
            )
            
            return {"task_id": response.result.id, "status": "success"}
                    
    except Exception as e:
        print(f"Error sending message to orchestrator: {e}")
        return {"status": "error", "message": str(e)}


async def get_task_status_from_orchestrator(orchestrator_url: Optional[str], task_id: str) -> Dict[str, Any]:
    """Gets the status of a task from the orchestrator agent using AgentSDK A2AClient."""
    try:
        # Import A2AClient
        try:
            from trento_agent_sdk.a2a_client import A2AClient
        except ImportError:
            print("AgentSDK not available, please install trento_agent_sdk")
            return {"status": "error", "error": "AgentSDK not available"}
        
        # Use environment variable if orchestrator_url is not provided
        if not orchestrator_url:
            orchestrator_url = os.getenv("ORCHESTRATOR_URL", "https://ai-design-orchestrator-595073969012.europe-west1.run.app")
        
        # Use A2AClient to get task status
        async with A2AClient(orchestrator_url) as client:
            task_response = await client.get_task(task_id)
            
            if task_response.result and task_response.result.status:
                task = task_response.result
                status = task.status.state
                content = None
                
                # Extract message content if available
                if task.status.message and task.status.message.parts:
                    for part in task.status.message.parts:
                        if hasattr(part, "text") and part.text:
                            content = part.text
                            break
                
                return {
                    "status": status, 
                    "content": content
                }
            else:
                return {"status": "unknown", "content": None}
                    
    except Exception as e:
        print(f"Error getting task status from orchestrator: {e}")
        return {"status": "error", "error": str(e)}


async def wait_for_orchestrator_task_completion(orchestrator_url: Optional[str], task_id: str, 
                                               timeout: Optional[float] = 60.0) -> Dict[str, Any]:
    """Wait for a task to complete and return the final result, similar to agent_client.py approach."""
    try:
        from config import ORCHESTRATOR_URL
        from trento_agent_sdk.a2a_client import A2AClient
        
        if not orchestrator_url:
            orchestrator_url = ORCHESTRATOR_URL
        
        if not orchestrator_url or orchestrator_url == "Not set":
            print(f"ERROR: Invalid orchestrator URL: '{orchestrator_url}'")
            return {"status": "error", "error": "Orchestrator URL is not configured properly"}

        async with A2AClient(orchestrator_url) as client:
            # Wait for the task to complete
            result = await client.wait_for_task_completion(task_id, timeout=timeout)
            
            if result.result and result.result.status and result.result.status.message:
                message = result.result.status.message
                if message.parts:
                    for part in message.parts:
                        if hasattr(part, "text") and part.text:
                            return {
                                "status": result.result.status.state, # Use the actual state
                                "content": part.text
                            }
                # If no text part found, but task completed
                return {"status": result.result.status.state, "content": "Task completed but no text content found"}
            elif result.result and result.result.status: # Task completed but no message parts
                 return {"status": result.result.status.state, "content": "Task completed without message content"}
            else:
                return {"status": "error", "error": "Task result or status not available in the expected format"}
                    
    except TimeoutError as e:
        print(f"Timeout waiting for task completion for task {task_id}: {e}")
        return {"status": "error", "error": f"Timeout waiting for task completion: {str(e)}"}
    except Exception as e:
        print(f"Error waiting for task completion for task {task_id}: {e}")
        return {"status": "error", "error": str(e)}
