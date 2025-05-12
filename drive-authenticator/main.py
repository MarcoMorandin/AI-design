import uvicorn
import os  # Ensure os is imported

# Adjust imports to be absolute for direct execution
# This assumes that when you run `python main.py`,
# the `drive-authenticator` directory is in your PYTHONPATH or is the current working directory.
# For simplicity and common use case, we'll assume `python main.py` is run from `drive-authenticator`.

from __init__ import app  # Import the app instance from __init__.py
from config import (
    FLASK_PORT,  # Keep for now, can be Uvicorn port
    REDIRECT_URI,
    SECRET_KEY,  # Needed for SessionMiddleware
)
from starlette.middleware.sessions import SessionMiddleware

# Add SessionMiddleware to the FastAPI app
# The secret_key is essential for signing the session cookie.
if SECRET_KEY:
    app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
else:
    print(
        "Warning: SECRET_KEY not set. Session middleware will not be secure. Please set FLASK_SECRET_KEY environment variable."
    )
    # Fallback for local dev if you absolutely must, but not recommended for production
    app.add_middleware(
        SessionMiddleware, secret_key="a_very_default_secret_key_for_dev_only"
    )

if __name__ == "__main__":
    print(f"Auth service running on http://localhost:{FLASK_PORT}")
    print(f"Ensure your Google OAuth redirect URI is set to: {REDIRECT_URI}")

    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    uvicorn.run(
        app, host="0.0.0.0", port=FLASK_PORT, log_level="info"
    )  # pragma: no cover
