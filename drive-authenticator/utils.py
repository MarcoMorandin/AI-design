from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Remove direct import of GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET from .config
# as they will come from the credentials dictionary.


# --- Helper Functions ---
def get_google_drive_service(session_credentials_dict):  # Renamed parameter for clarity
    """Builds and returns a Google Drive service object."""
    # Construct Credentials object using values from the session_credentials_dict
    creds = Credentials(
        token=session_credentials_dict["access_token"],
        refresh_token=session_credentials_dict.get("refresh_token"),
        token_uri=session_credentials_dict["token_uri"],
        client_id=session_credentials_dict["client_id"],
        client_secret=session_credentials_dict["client_secret"],
        scopes=session_credentials_dict["scopes"],  # This is already a list of scopes
    )
    # The googleapiclient will handle token refresh if the Credentials object is properly configured
    # with a refresh_token and token_uri.
    return build("drive", "v3", credentials=creds)


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
