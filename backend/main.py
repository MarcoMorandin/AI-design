import uvicorn
import os
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()

# Import app and config after loading environment variables
from __init__ import app
from config import (
    PORT,
    REDIRECT_URI,
    SECRET_KEY,
    ENVIRONMENT,
    FRONTEND_URL,
)

# Add SessionMiddleware to the FastAPI app
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set for production deployment")

# Add SessionMiddleware first (inner-most middleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Parse the frontend URL to extract the origin
frontend_origin = urlparse(FRONTEND_URL).scheme + "://" + urlparse(FRONTEND_URL).netloc if FRONTEND_URL else "http://localhost:3000"

# Add CORS middleware (outer middleware) - with wildcard to allow all localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
)

if __name__ == "__main__":
    print(f"Auth service running on port: {PORT}")
    print(f"Google OAuth redirect URI: {REDIRECT_URI}")

    # Only disable HTTPS verification in development
    if ENVIRONMENT == "development":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        print("WARNING: Running in development mode with insecure transport")
    else:
        # Make sure HTTPS is required in production
        if os.environ.get("OAUTHLIB_INSECURE_TRANSPORT") == "1":
            os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT")

    # Use different settings based on environment
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info" if ENVIRONMENT == "development" else "info",
    )  # pragma: no cover