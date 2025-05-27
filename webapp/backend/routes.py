import datetime
from fastapi import HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.requests import Request
from pymongo import ReturnDocument
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.auth.exceptions

# Adjust imports to be absolute for direct execution from main.py
from __init__ import app
from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    REDIRECT_URI,
    SCOPES,
    DRIVE_FOLDER_BASENAME,
    ENVIRONMENT,
    FRONTEND_URL,
)
from utils import (
    get_google_drive_service, 
    create_drive_folder_if_not_exists,
    get_folder_structure,
    get_courses,
    get_course_structure,
    send_message_to_orchestrator,
    get_task_status_from_orchestrator,
    wait_for_orchestrator_task_completion,
    subscribe_folder_to_webhook
)
from models import (
    UserProfile, 
    FolderStructure,
    FolderItem,
    Course, 
    CourseList,
    CourseFolderStructure,
    OrchestratorMessage,
    OrchestratorResponse,
    TaskStatusResponse
)
from auth_middleware import (
    create_access_token, 
    get_current_user,
    Token,
    TokenData,
    oauth2_scheme,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


# CORS middleware is now configured in main.py


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


@app.get("/api")
async def api_root():
    """API root with available endpoints"""
    return {
        "message": "Drive Authenticator API",
        "version": "1.0.0",
        "endpoints": {
            "auth": [
                "/api/auth/google",
                "/api/auth/google/callback",
                "/api/auth/token",
                "/api/auth/refresh",
            ],
            "user": [
                "/api/user/profile",
                "/api/user/folders",
                "/api/user/courses",
                "/api/user/courses/{course_name}",
            ],
            "orchestrator": [
                "/api/orchestrator/message",
            ]
        }
    }


# -------------------- Authentication Endpoints --------------------

@app.get("/api/auth/google")
async def login_google(request: Request):
    """Endpoint to initiate Google OAuth flow"""
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


@app.get("/api/auth/google/callback")
async def oauth2callback(
    request: Request,
    state: str = None,
    error: str = None,
):
    """Google OAuth callback endpoint"""
    session_state = request.session.pop("oauth_state", None)

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
        redirect_uri=REDIRECT_URI,
    )

    try:
        # Ensure the full URL is passed as a string
        flow.fetch_token(authorization_response=str(request.url))
    except google.auth.exceptions.OAuthError as e:
        print(f"OAuthError during token fetch: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Google's error response: {e.response.json()}")
            except Exception:
                print(f"Could not parse Google's error response as JSON: {e.response.text}")
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
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
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
        folder_id = create_drive_folder_if_not_exists(drive_service, folder_name_with_id)

        if folder_id:
            # Access users_collection from app.state
            current_users_collection = request.app.state.users_collection
            current_users_collection.update_one(
                {"googleId": google_id},
                {
                    "$set": {
                        "driveFolderId": folder_id,
                        "driveFolderName": folder_name_with_id,
                    }
                },
            )
            print(f"Successfully created/verified Drive folder '{folder_name_with_id}' with ID: {folder_id}")
            
            # Subscribe the folder to the drive-webhook service for monitoring changes
            subscription_success = subscribe_folder_to_webhook(google_id)
            if subscription_success:
                print(f"Successfully subscribed folder '{folder_name_with_id}' to drive-webhook for user {google_id}")
            else:
                print(f"Failed to subscribe folder '{folder_name_with_id}' to drive-webhook for user {google_id}")
        else:
            print(f"Failed to create or verify Google Drive folder for user {google_id}.")
    else:
        print("Failed to get Google Drive service. Cannot create folder.")

    # Create JWT access token for the user with user info
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": google_id,
            "email": email,
            "name": display_name
        }, 
        expires_delta=access_token_expires
    )
    
    print(f"Generated access token for user {google_id} (email: {email})")
    
    # Build the redirect URL with token parameter
    redirect_url = f"{FRONTEND_URL}/auth/callback?token={access_token}"
    print(f"Redirecting to: {redirect_url}")
    
    return RedirectResponse(url=redirect_url)


@app.post("/api/auth/token", response_model=Token)
async def login_for_access_token(request: Request):
    """Generate a new access token using session credentials"""
    if "credentials" not in request.session or "google_id" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login first.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    google_id = request.session["google_id"]
    
    # Create access token
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": google_id}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/refresh", response_model=Token)
async def refresh_token(token: str = Depends(oauth2_scheme)):
    """Refresh an existing access token"""
    try:
        # Validate the existing token
        payload = await get_current_user(token)
        
        # Create a new access token
        access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": payload.google_id}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token for refresh",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/api/auth/logout")
async def logout(request: Request):
    """Logout endpoint that clears the session"""
    request.session.pop("credentials", None)
    request.session.pop("user_id", None)
    request.session.pop("google_id", None)
    
    return {"message": "Successfully logged out"}


# -------------------- User Profile Endpoints --------------------

@app.get("/api/user/profile", response_model=UserProfile)
async def get_user_profile(request: Request, token_data: TokenData = Depends(get_current_user)):
    """Get the profile information of the current logged-in user"""
    users_collection = request.app.state.users_collection
    user = users_collection.find_one({"googleId": token_data.google_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserProfile(
        user_id=str(user["_id"]),
        google_id=user["googleId"],
        email=user["email"],
        display_name=user["displayName"],
        drive_folder_id=user.get("driveFolderId"),
        drive_folder_name=user.get("driveFolderName"),
        created_at=user.get("createdAt")
    )


# -------------------- Folder Structure Endpoints --------------------

@app.get("/api/user/folders", response_model=FolderStructure)
async def get_user_folders(request: Request, token_data: TokenData = Depends(get_current_user)):
    """Get the folder structure for the user's Drive folder"""
    users_collection = request.app.state.users_collection
    user = users_collection.find_one({"googleId": token_data.google_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if we have a Drive folder ID for the user
    folder_id = user.get("driveFolderId")
    if not folder_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drive folder not found for user",
        )
    
    # Try to get Google credentials (first from session, then from DB if needed)
    credentials = None
    if "credentials" in request.session:
        credentials = request.session["credentials"]
    else:
        # Try to get credentials from the database
        print(f"No Google Drive credentials in session for user {token_data.google_id}, trying database")
        if user and "googleTokens" in user:
            credentials = user.get("googleTokens")
            # Store the credentials in the session for future requests
            request.session["credentials"] = credentials
            print(f"Retrieved Google Drive credentials from database for user {token_data.google_id}")
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated with Google Drive. Please login again.",
        )
    
    # Get the Google Drive service
    drive_service = get_google_drive_service(credentials)
    if not drive_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize Google Drive service",
        )
    
    # Get the folder structure
    folder_items = get_folder_structure(drive_service, folder_id)
    
    # Convert to response model
    items = []
    for item in folder_items:
        items.append(FolderItem(
            id=item["id"],
            name=item["name"],
            mime_type=item["mimeType"],
            is_folder=item["isFolder"]
        ))
    
    return FolderStructure(
        folder_id=folder_id,
        folder_name=user.get("driveFolderName", ""),
        items=items
    )


# -------------------- Courses Endpoints --------------------

@app.get("/api/user/courses", response_model=CourseList)
async def get_user_courses(request: Request, token_data: TokenData = Depends(get_current_user)):
    """Get all courses (top-level folders) in the user's Drive folder"""
    users_collection = request.app.state.users_collection
    user = users_collection.find_one({"googleId": token_data.google_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if we have a Drive folder ID for the user
    folder_id = user.get("driveFolderId")
    if not folder_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drive folder not found for user",
        )
    
    # Try to get Google credentials (first from session, then from DB if needed)
    credentials = None
    
    # Check if we have Google credentials in session
    if "credentials" in request.session:
        credentials = request.session["credentials"]
        print(f"Using credentials from session for user {token_data.google_id}")
    else:
        # Try to get credentials from the database
        print(f"No Google Drive credentials in session for user {token_data.google_id}, trying database")
        if user and "googleTokens" in user:
            credentials = user.get("googleTokens")
            
            # Ensure the token_uri is present
            if "token_uri" not in credentials:
                credentials["token_uri"] = "https://oauth2.googleapis.com/token"
                print("Added missing token_uri to credentials from database")
                
            # Store the enhanced credentials in the session for future requests
            request.session["credentials"] = credentials
            print(f"Retrieved Google Drive credentials from database for user {token_data.google_id}")
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated with Google Drive. Please login again.",
        )
    
    # Get the Google Drive service
    drive_service = get_google_drive_service(credentials)
    if not drive_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize Google Drive service",
        )
    
    # Get the courses (top-level folders)
    course_items = get_courses(drive_service, folder_id)
    
    # Convert to response model
    courses = []
    for course in course_items:
        courses.append(Course(
            id=course["id"],
            name=course["name"]
        ))
    
    return CourseList(courses=courses)


@app.get("/api/user/courses/{course_id}", response_model=CourseFolderStructure)
async def get_course_folder_structure(
    course_id: str, 
    request: Request, 
    token_data: TokenData = Depends(get_current_user)
):
    """Get the folder structure for a specific course"""
    users_collection = request.app.state.users_collection
    user = users_collection.find_one({"googleId": token_data.google_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Try to get Google credentials (first from session, then from DB if needed)
    credentials = None
    
    # Check if we have Google credentials in session
    if "credentials" in request.session:
        credentials = request.session["credentials"]
        print(f"Using credentials from session for user {token_data.google_id}")
    else:
        # Try to get credentials from the database
        print(f"No Google Drive credentials in session for user {token_data.google_id}, trying database")
        if user and "googleTokens" in user:
            credentials = user.get("googleTokens")
            
            # Ensure the token_uri is present
            if "token_uri" not in credentials:
                credentials["token_uri"] = "https://oauth2.googleapis.com/token"
                print("Added missing token_uri to credentials from database")
                
            # Store the enhanced credentials in the session for future requests
            request.session["credentials"] = credentials
            print(f"Retrieved Google Drive credentials from database for user {token_data.google_id}")
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated with Google Drive. Please login again.",
        )
    
    # Get the Google Drive service
    drive_service = get_google_drive_service(credentials)
    if not drive_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize Google Drive service",
        )
    
    # First, verify this course belongs to the user
    user_folder_id = user.get("driveFolderId")
    if not user_folder_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drive folder not found for user",
        )
    
    # Get course information to verify it exists and get its name
    course_info = None
    try:
        course_info = drive_service.files().get(fileId=course_id, fields="id,name,parents").execute()
    except HttpError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or you don't have access to it",
        )
    
    # Check if the course is a direct child of the user's folder
    if user_folder_id not in course_info.get("parents", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this course",
        )
    
    # Get the course structure
    course_items = get_course_structure(drive_service, course_id)
    
    # Convert to response model with hierarchical structure
    def convert_to_folder_item(item_data):
        return FolderItem(
            id=item_data["id"],
            name=item_data["name"],
            mime_type=item_data["mimeType"],
            is_folder=item_data["isFolder"],
            children=[convert_to_folder_item(child) for child in item_data.get("children", [])]
        )
    
    items = []
    for item in course_items:
        items.append(convert_to_folder_item(item))
    
    return CourseFolderStructure(
        course_id=course_id,
        course_name=course_info["name"],
        items=items
    )


# -------------------- Orchestrator Endpoints --------------------

@app.post("/api/orchestrator/message", response_model=OrchestratorResponse)
async def send_orchestrator_message(
    message: OrchestratorMessage,
    request: Request,
    token_data: TokenData = Depends(get_current_user)
):
    """Send a message to the orchestrator agent"""
    users_collection = request.app.state.users_collection
    user = users_collection.find_one({"googleId": token_data.google_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Validate user_id
    if not message.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required in the request body",
        )
    
    # Send message to orchestrator
    orchestrator_url = None  # Will use default from environment in utils.py
    response = await send_message_to_orchestrator(
        orchestrator_url=orchestrator_url,
        message=message.message,
        user_id=message.user_id,
        session_id=message.session_id,
        params=message.params
    )
    
    if response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response.get("message", "Failed to send message to orchestrator")
        )
    
    return OrchestratorResponse(
        task_id=response.get("task_id", ""),
        status="success"
    )

@app.get("/api/orchestrator/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    request: Request,
    token_data: TokenData = Depends(get_current_user)
):
    """Get the status of a task from the orchestrator agent"""
    # Get task status from orchestrator
    orchestrator_url = None  # Will use default from environment in utils.py
    response = await get_task_status_from_orchestrator(
        orchestrator_url=orchestrator_url,
        task_id=task_id
    )
    
    return TaskStatusResponse(
        status=response.get("status", "error"),
        content=response.get("content"),
        error=response.get("error")
    )

@app.post("/api/orchestrator/message/wait", response_model=OrchestratorResponse)
async def send_orchestrator_message_wait(
    message: OrchestratorMessage,
    request: Request,
    token_data: TokenData = Depends(get_current_user)
):
    """Send a message to the orchestrator agent and wait for completion"""
    users_collection = request.app.state.users_collection
    user = users_collection.find_one({"googleId": token_data.google_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Validate user_id
    if not message.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required in the request body",
        )
    
    # Send message to orchestrator
    orchestrator_url = None  # Will use default from environment in utils.py
    response = await send_message_to_orchestrator(
        orchestrator_url=orchestrator_url,
        message=message.message,
        user_id=message.user_id,
        session_id=message.session_id,
        params=message.params
    )
    
    if response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response.get("message", "Failed to send message to orchestrator")
        )
    
    task_id = response.get("task_id", "")
    
    # Wait for the orchestrator task to complete
    wait_response = await wait_for_orchestrator_task_completion(
        orchestrator_url=orchestrator_url,
        task_id=task_id
    )
    
    return OrchestratorResponse(
        task_id=task_id,
        status=wait_response.get("status", "error"),
        content=wait_response.get("content"),
        error=wait_response.get("error")
    )

@app.post("/api/orchestrator/message_and_wait", response_model=TaskStatusResponse)
async def send_orchestrator_message_and_wait(
    message: OrchestratorMessage, # Reuse the same model as /message
    request: Request,
    token_data: TokenData = Depends(get_current_user)
):
    """Send a message to the orchestrator agent and wait for completion."""
    users_collection = request.app.state.users_collection
    user = users_collection.find_one({"googleId": token_data.google_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not message.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required in the request body",
        )
    
    orchestrator_url = None # Will use default from environment
    
    # 1. Send the initial task
    send_response = await send_message_to_orchestrator(
        orchestrator_url=orchestrator_url,
        message=message.message,
        user_id=message.user_id,
        session_id=message.session_id,
        params=message.params
    )
    
    if send_response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=send_response.get("message", "Failed to send initial message to orchestrator")
        )
    
    task_id = send_response.get("task_id")
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task_id from orchestrator after sending message"
        )
        
    # 2. Wait for the task to complete
    # You might want to adjust the timeout value
    completion_response = await wait_for_orchestrator_task_completion(
        orchestrator_url=orchestrator_url, 
        task_id=task_id,
        timeout=120.0  # Example timeout of 120 seconds
    )
    
    return TaskStatusResponse(
        status=completion_response.get("status", "error"),
        content=completion_response.get("content"),
        error=completion_response.get("error")
    )

# Keep legacy routes for backward compatibility
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Legacy index route for backward compatibility"""
    return """
    <html>
        <head>
            <title>Drive Authenticator API</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                h1 {
                    color: #1a73e8;
                }
                .api-list {
                    background-color: #f1f3f4;
                    padding: 15px;
                    border-radius: 5px;
                }
                a {
                    color: #1a73e8;
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <h1>Drive Authenticator API</h1>
            <p>This service provides RESTful APIs for Google Drive authentication and folder management.</p>
            <div class="api-list">
                <h2>Available Endpoints</h2>
                <p>The main API is available at: <a href="/api">/api</a></p>
                <p>For authentication: <a href="/api/auth/google">/api/auth/google</a></p>
            </div>
        </body>
    </html>
    """
