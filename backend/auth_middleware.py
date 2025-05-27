import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

# Setup OAuth2 password bearer scheme with auto_error=False to handle token errors in our code
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token", auto_error=False)

# JWT configuration
# This should be loaded from env variables in production, but we hardcode for development
JWT_SECRET_KEY = "ai-design-project-secret-key-2025"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    google_id: Optional[str] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT token with given payload and expiration time"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate the JWT token and return user info"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Handle missing token case since we set auto_error=False
    if not token:
        print("No token provided")
        raise credentials_exception
        
    try:
        # Print debug information
        print(f"Validating token: {token[:10]}...")
        
        # Decode and verify JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Get Google ID from token
        google_id: str = payload.get("sub")
        if google_id is None:
            print("Token missing 'sub' claim (google_id)")
            raise credentials_exception
            
        print(f"Successfully validated token for user: {google_id}")
        token_data = TokenData(google_id=google_id)
        return token_data
        
    except jwt.ExpiredSignatureError:
        print("Token validation failed: Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        print(f"Token validation failed: {str(e)}")
        raise credentials_exception
    except Exception as e:
        print(f"Unexpected error during token validation: {str(e)}")
        raise credentials_exception
