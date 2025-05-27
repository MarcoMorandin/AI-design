import datetime
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

# --- Configuration ---
from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
)

# --- Logging Setup ---
logger = logging.getLogger(__name__)


def get_google_credentials_from_db(
    user_google_id, users_collection
):  # Added users_collection parameter
    """Fetches user's Google tokens from MongoDB and refreshes if necessary."""
    if users_collection is None:  # Check the passed collection
        logger.warning(
            "User collection not available in utils (was not passed or is None)."
        )
        return None

    user = users_collection.find_one({"googleId": user_google_id})
    if not user or "googleTokens" not in user:
        logger.warning(f"User {user_google_id} not found or no tokens stored.")
        return None

    tokens = user["googleTokens"]

    expiry_datetime = None
    if tokens.get("expiry_date"):
        try:
            # expiry_date is expected to be a Unix timestamp (seconds since epoch, UTC)
            # Convert to naive UTC datetime to align with google-auth's internal utcnow()
            expiry_datetime = datetime.datetime.utcfromtimestamp(
                float(tokens["expiry_date"])
            )
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Warning: Could not parse expiry_date '{tokens['expiry_date']}' for user {user_google_id}: {e}"
            )
            # expiry_datetime remains None if parsing fails

    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",  # Standard token URI
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=(
            tokens.get("scope").split()
            if isinstance(tokens.get("scope"), str)
            else tokens.get("scope")
        ),
        expiry=expiry_datetime,
    )

    if creds.expired and creds.refresh_token:
        logger.info(f"Token for user {user_google_id} expired. Refreshing...")
        try:
            creds.refresh(Request())
            # Save the refreshed tokens back to the database
            new_token_data = {
                "googleTokens.access_token": creds.token,
            }
            if creds.expiry:
                # Store expiry as a Unix timestamp (seconds since epoch, UTC)
                # If creds.expiry is naive (likely if 'expires_in' was used during refresh),
                # it represents UTC. Make it offset-aware (UTC) before calling timestamp()
                # to ensure the timestamp is correctly calculated from UTC.
                current_creds_expiry = creds.expiry
                if current_creds_expiry.tzinfo is None:  # Check if naive
                    current_creds_expiry = current_creds_expiry.replace(
                        tzinfo=datetime.timezone.utc
                    )
                new_token_data["googleTokens.expiry_date"] = (
                    current_creds_expiry.timestamp()
                )

            # Potentially, if the refresh token itself could be rotated (though rare for Google's flow unless revoked):
            # if creds.refresh_token != tokens.get("refresh_token"):
            #    new_token_data["googleTokens.refresh_token"] = creds.refresh_token

            users_collection.update_one(  # Use the passed users_collection
                {"googleId": user_google_id}, {"$set": new_token_data}
            )
            logger.info(f"Token for user {user_google_id} refreshed and updated in DB.")
        except RefreshError as e:
            logger.error(f"Error refreshing token for user {user_google_id}: {e}")
            # Potentially mark the user as needing re-authentication
            return None
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during token refresh for user {user_google_id}: {e}"
            )
            return None
    return creds


def get_google_drive_service(credentials):
    """Builds and returns a Google Drive service object."""
    if not credentials:
        logger.error("Cannot build Google Drive service without credentials.")
        return None
    try:
        # Pass credentials directly. The google-api-python-client library,
        # using google-auth, should handle the HTTP transport.
        # If 'certifi' is installed, google-auth's default 'requests' transport
        # (or httplib2 if configured) should pick it up.
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        logger.error(f"Error building Google Drive service: {e}")
        return None
