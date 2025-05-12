import os
from dotenv import load_dotenv

load_dotenv()

# Flask app configuration
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
FLASK_PORT = int(os.environ.get("AUTH_SERVICE_PORT", 5000))
# Reverting BASE_URL to HTTP for local development without SSL
# WARNING: This is insecure and should only be used for local development.
# Ensure your Google Cloud Console redirect URI is also set to HTTP.
BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{FLASK_PORT}")

# MongoDB configuration
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = f"{BASE_URL}/auth/google/callback"  # Will now use http
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

# Name for the Drive folder
DRIVE_FOLDER_BASENAME = "MoodleAI"
