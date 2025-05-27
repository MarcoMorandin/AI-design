import os
from dotenv import load_dotenv

load_dotenv()

# Environment configuration
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# App configuration
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
PORT = int(os.environ.get("PORT", 3000))

# Base URL configuration - set to HTTPS in production
BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{PORT}")

# MongoDB configuration
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = f"{BASE_URL}/api/auth/google/callback"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

# Name for the Drive folder
DRIVE_FOLDER_BASENAME = "MoodleAI"

# Frontend URL configuration
FRONTEND_URL = os.environ.get("FRONTEND_URL")

# Orchestrator URL configuration
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL")

# Drive webhook service URL configuration
DRIVE_WEBHOOK_URL = os.environ.get("DRIVE_WEBHOOK_URL", "http://localhost:5001")
