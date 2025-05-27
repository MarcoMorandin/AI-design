import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Application configuration
PORT = int(
    os.environ.get("PORT", 5001)
)  # Renamed from FLASK_PORT_WATCHER
# IMPORTANT! For Google Notifications - This should be your public ngrok URL (e.g., https://xxxx-xx-xxx-xxx-xx.ngrok-free.app)
WATCHER_SERVICE_PUBLIC_URL = os.environ.get("BASE_URL")

# MongoDB configuration
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")

# Google OAuth configuration (shared with utils.py, consider a single source of truth if this grows)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
