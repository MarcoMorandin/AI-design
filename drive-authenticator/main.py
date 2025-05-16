import uvicorn
import os

from __init__ import app
from config import (
    PORT,
    REDIRECT_URI,
    SECRET_KEY,
    ENVIRONMENT,
)
from starlette.middleware.sessions import SessionMiddleware

# Add SessionMiddleware to the FastAPI app
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set for production deployment")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

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
