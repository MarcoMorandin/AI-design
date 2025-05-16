import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.requests import Request
from pymongo import ReturnDocument
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.auth.exceptions  # Import the exceptions module

# Adjust imports to be absolute for direct execution from main.py
# Remove users_collection from here, it will be accessed via request.app.state
from __init__ import app

from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    REDIRECT_URI,
    SCOPES,
    DRIVE_FOLDER_BASENAME,
    ENVIRONMENT,
)
from utils import get_google_drive_service, create_drive_folder_if_not_exists


# Health check endpoint for Docker
@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint for monitoring and Docker healthchecks"""
    health_data = {
        "status": "ok",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "environment": ENVIRONMENT,
        "service": "drive-authenticator",
    }

    # Optionally check database connection if required
    mongo_status = "unknown"
    try:
        if (
            hasattr(request.app.state, "users_collection")
            and request.app.state.users_collection
        ):
            # Simple ping to check if MongoDB is responsive
            result = request.app.state.users_collection.database.command("ping")
            if result.get("ok") == 1.0:
                mongo_status = "connected"
            else:
                mongo_status = "error"
    except Exception as e:
        mongo_status = f"error: {str(e)}"

    health_data["database"] = mongo_status

    return JSONResponse(content=health_data)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    print(request.app.state.users_collection)
    if "credentials" in request.session:
        # FastAPI's url_for is accessed via request.url_for
        # For simplicity, using hardcoded paths for now.
        return f"""Hello! You are logged in. <a href="/logout">Logout</a> <br/> <a href="/profile">View Profile</a>"""
    return f"""Welcome! <a href="/login/google">Login with Google</a>"""


@app.get("/login/google")
async def login_google(request: Request):
    if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID == "YOUR_GOOGLE_CLIENT_ID":
        raise HTTPException(
            status_code=500, detail="Error: Google Client ID not configured."
        )

    # Use Flow.from_client_config when client_config is provided
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent"
    )
    request.session["oauth_state"] = state
    return RedirectResponse(authorization_url)


@app.get("/auth/google/callback")
async def oauth2callback(
    request: Request,
    state: str = None,
    error: str = None,
    error_reason: str = None,
    error_description: str = None,
):
    session_state = request.session.pop("oauth_state", None)

    # FastAPI automatically gets query params like 'state'.
    # The 'state' param in function signature comes from request.query_params.get('state')
    query_state = request.query_params.get("state")

    if not session_state or session_state != query_state:
        raise HTTPException(
            status_code=400, detail="Invalid state parameter. CSRF attack suspected."
        )

    query_error = request.query_params.get("error")
    if query_error:
        error_reason_val = request.query_params.get("error_reason", "Unknown error")
        error_description_val = request.query_params.get("error_description", "")
        raise HTTPException(
            status_code=400,
            detail=f"Error during Google authentication: {error_reason_val} - {error_description_val}",
        )

    # Use Flow.from_client_config when client_config is provided
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,  # This should be the full URL of this callback
    )

    try:
        # request.url gives the full URL of the current request
        # Ensure the full URL is passed as a string
        flow.fetch_token(authorization_response=str(request.url))
    except google.auth.exceptions.OAuthError as e:  # Catch specific OAuthError
        print(f"OAuthError during token fetch: {e}")
        print(
            f"Error details: {getattr(e, 'details', 'No additional details')}"
        )  # Attempt to get more details
        # If the error object has a response attribute, it might contain the server's response
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Google's error response: {e.response.json()}")
            except Exception as json_e:
                print(
                    f"Could not parse Google's error response as JSON: {e.response.text}"
                )
        raise HTTPException(status_code=500, detail=f"Failed to fetch OAuth token: {e}")
    except Exception as e:
        print(f"Generic error fetching token: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch OAuth token due to an unexpected error: {e}",
        )

    credentials = flow.credentials
    request.session["credentials"] = {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "expiry_date": credentials.expiry.timestamp(),
    }

    try:
        user_info_service = build("oauth2", "v2", credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
    except HttpError as e:
        print(f"Error fetching user info: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch user information from Google."
        )

    google_id = user_info.get("id")
    email = user_info.get("email")
    display_name = user_info.get("name") or user_info.get("given_name")

    if not google_id or not email:
        raise HTTPException(
            status_code=500, detail="Could not retrieve Google ID or email."
        )

    user_data = {
        "googleId": google_id,
        "displayName": display_name,
        "email": email,
        "googleTokens": {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expiry_date": credentials.expiry.timestamp(),
            "scope": " ".join(credentials.scopes),
            "token_type": "Bearer",
        },
    }

    # Access users_collection from app.state
    current_users_collection = request.app.state.users_collection
    if current_users_collection is None:
        raise HTTPException(
            status_code=500, detail="Database not configured. Cannot save user."
        )

    existing_user = current_users_collection.find_one_and_update(
        {"googleId": google_id},
        {"$set": user_data, "$setOnInsert": {"createdAt": datetime.datetime.utcnow()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    request.session["user_id"] = str(existing_user["_id"])
    request.session["google_id"] = google_id

    drive_service = get_google_drive_service(request.session["credentials"])
    if drive_service:
        folder_name_with_id = f"{DRIVE_FOLDER_BASENAME}_{google_id}"
        folder_id = create_drive_folder_if_not_exists(
            drive_service, folder_name_with_id
        )

        if folder_id:
            # Access users_collection from app.state
            current_users_collection = request.app.state.users_collection
            if (
                current_users_collection is None
            ):  # Should not happen if previous check passed, but good for safety
                raise HTTPException(
                    status_code=500,
                    detail="Database not configured. Cannot update user with folder ID.",
                )
            current_users_collection.update_one(
                {"googleId": google_id},
                {
                    "$set": {
                        "driveFolderId": folder_id,
                        "driveFolderName": folder_name_with_id,
                    }
                },
            )
            print(
                f"Successfully created/verified Drive folder '{folder_name_with_id}' with ID: {folder_id}"
            )
        else:
            print(
                f"Failed to create or verify Google Drive folder for user {google_id}."
            )
    else:
        print("Failed to get Google Drive service. Cannot create folder.")

    return RedirectResponse(
        url="/profile", status_code=303
    )  # Use 303 See Other for POST-redirect-GET


@app.get("/profile")  # FastAPI automatically converts dict to JSON response
async def profile(request: Request):
    if "credentials" not in request.session or "user_id" not in request.session:
        return RedirectResponse(
            url="/login/google", status_code=307
        )  # Temporary redirect

    # Access users_collection from app.state
    current_users_collection = request.app.state.users_collection
    if current_users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured.")

    user = current_users_collection.find_one(
        {"googleId": request.session.get("google_id")}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Mask sensitive tokens for display
    if user.get("googleTokens"):
        user["googleTokens"]["access_token"] = "********"
        user["googleTokens"]["refresh_token"] = "********"

    user["_id"] = str(user["_id"])
    if "createdAt" in user and isinstance(user["createdAt"], datetime.datetime):
        user["createdAt"] = user["createdAt"].isoformat()

    return user  # FastAPI will serialize this dict to JSON


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
