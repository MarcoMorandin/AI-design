"""
Google Authentication utilities for the Drive Organizer service.
This module provides common functions for handling Google OAuth credentials and token refresh.
"""

import os
import logging
from typing import Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def create_and_refresh_credentials(google_tokens: Dict[str, Any]) -> Credentials:
    """Create Google credentials and refresh if needed.
    
    Args:
        google_tokens: Dictionary containing Google OAuth tokens
        
    Returns:
        Credentials: Valid Google OAuth2 credentials
        
    Raises:
        ValueError: If required credentials are missing
        RefreshError: If token refresh fails
    """
    # Log available token keys for debugging (without sensitive values)
    logger.debug(f"Available token keys: {list(google_tokens.keys())}")
    
    # Validate required credentials
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.error("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET environment variables")
        raise ValueError("Google OAuth client credentials not configured")
    
    if not google_tokens.get("access_token"):
        logger.error("No access token found in user credentials")
        raise ValueError("No access token available")
    
    credentials = Credentials(
        token=google_tokens.get("access_token"),
        refresh_token=google_tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    
    # Check if credentials are expired and refresh if needed
    if credentials.expired and credentials.refresh_token:
        logger.info("Token expired. Attempting to refresh...")
        try:
            credentials.refresh(Request())
            logger.info("Token refreshed successfully")
        except RefreshError as e:
            logger.error(f"Failed to refresh token: {e}")
            # Provide more specific error message based on the error
            if "invalid_client" in str(e):
                raise RefreshError(f"Invalid client credentials. Please check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET: {e}")
            elif "unauthorized_client" in str(e):
                raise RefreshError(f"OAuth client not authorized. The Google OAuth app may need approval or the client configuration is incorrect. Please check Google Cloud Console OAuth settings: {e}")
            elif "invalid_grant" in str(e):
                raise RefreshError(f"Invalid or expired refresh token. User needs to re-authenticate: {e}")
            else:
                raise RefreshError(f"Token refresh failed: {e}")
    elif credentials.expired and not credentials.refresh_token:
        logger.error("Token expired but no refresh token available")
        raise RefreshError("Token expired and no refresh token available. User needs to re-authenticate.")
    
    return credentials


def validate_google_tokens(google_tokens: Dict[str, Any]) -> bool:
    """Validate that the required Google tokens are present.
    
    Args:
        google_tokens: Dictionary containing Google OAuth tokens
        
    Returns:
        bool: True if tokens are valid, False otherwise
    """
    required_fields = ["access_token"]
    
    for field in required_fields:
        if not google_tokens.get(field):
            logger.warning(f"Missing required token field: {field}")
            return False
    
    logger.debug(f"Google tokens validation passed. Available fields: {list(google_tokens.keys())}")
    return True
