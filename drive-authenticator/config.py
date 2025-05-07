import os
from dotenv import load_dotenv

load_dotenv()

# Environment configuration
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# App configuration
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
PORT = int(os.environ.get("AUTH_SERVICE_PORT", 5000))

# Base URL configuration - set to HTTPS in production
if ENVIRONMENT == "production":
    # In production, BASE_URL should be HTTPS
    BASE_URL = os.environ.get("BASE_URL")
    if not BASE_URL:
        raise ValueError("BASE_URL environment variable must be set in production")
    if not BASE_URL.startswith("https://"):
        raise ValueError("BASE_URL must use HTTPS in production")
else:
    # Only for development
    BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{PORT}")

# MongoDB configuration
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")

# Ensure MongoDB configuration is set in production
if ENVIRONMENT == "production" and (not MONGO_URI or not MONGO_DB_NAME):
    raise ValueError("MongoDB configuration is required for production")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = f"{BASE_URL}/auth/google/callback"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

# Ensure OAuth credentials are set in production
if ENVIRONMENT == "production" and (not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET):
    raise ValueError("Google OAuth credentials are required for production")

# Name for the Drive folder
DRIVE_FOLDER_BASENAME = "MoodleAI"
