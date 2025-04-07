# app/utils/file_handler.py
import os
import shutil
import uuid
import logging
from pathlib import Path
from fastapi import HTTPException
from app.core.config import settings
from typing import Optional # Added for type hinting
import httpx # Make sure httpx is imported
from app.core.config import settings
from pydantic import HttpUrl # Added HttpUrl
from typing import Union # <--- Import Union

logger = logging.getLogger(__name__)

def get_temp_audio_path(base_filename: Path) -> Path:
    """Generates a path for the temporary audio file based on the video filename."""
    return settings.TEMP_DIR / f"{base_filename.stem}_extracted_audio.mp3"

def cleanup_files(*file_paths: Union[Path, str, None]):
    """Safely removes files, ignoring errors if files don't exist."""
    for file_path in file_paths:
        if file_path:
            path = Path(file_path) # Ensure it's a Path object
            if path.exists() and path.is_file(): # Check if it exists and is a file
                try:
                    path.unlink() # Use Path.unlink()
                    logger.info(f"Cleaned up temporary file: {path}")
                except OSError as e:
                    logger.error(f"Error cleaning up file {path}: {e}")
            # Optionally log if file not found, but usually cleanup shouldn't error if file is missing
            # else:
            #     logger.warning(f"Cleanup requested but file not found or not a file: {path}")
            
            
# --- New Download Function ---
async def download_video_from_url(video_url: HttpUrl) -> Path:
    """Downloads a video from a URL to a temporary file."""
    request_id = uuid.uuid4()
    # Try to guess a reasonable extension, default to .mp4 if unsure
    suffix = Path(video_url.path).suffix if Path(video_url.path).suffix else ".mp4"
    # Ensure suffix starts with a dot and is simple
    if not suffix.startswith(".") or len(suffix) > 5:
        suffix = ".mp4"

    temp_file_path = settings.TEMP_DIR / f"{request_id}_downloaded{suffix}"
    logger.info(f"Attempting to download video from {video_url} to {temp_file_path}")

    download_timeout = httpx.Timeout(settings.DOWNLOAD_TIMEOUT, connect=settings.DOWNLOAD_TIMEOUT)
    # Set limits: follow redirects, limit connections
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

    try:
        async with httpx.AsyncClient(timeout=download_timeout, limits=limits, follow_redirects=True) as client:
            async with client.stream("GET", str(video_url)) as response:
                # Check if the request was successful
                response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx

                # Optional: Check Content-Type
                content_type = response.headers.get("content-type", "").lower()
                if settings.ALLOWED_VIDEO_CONTENT_TYPES and not any(allowed_type in content_type for allowed_type in settings.ALLOWED_VIDEO_CONTENT_TYPES):
                     # Allow skipping check if content_type is generic (e.g., application/octet-stream)
                     if content_type != "application/octet-stream":
                        logger.warning(f"Disallowed content-type '{content_type}' for URL {video_url}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported content type: {content_type}. Allowed types start with: {settings.ALLOWED_VIDEO_CONTENT_TYPES}"
                        )
                     else:
                         logger.warning(f"Generic content-type '{content_type}', proceeding with download for URL {video_url}")


                # Optional: Check Content-Length for size limit
                content_length = response.headers.get("content-length")
                max_size_bytes = settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
                if content_length and int(content_length) > max_size_bytes:
                    logger.warning(f"Content-Length {content_length} exceeds limit of {max_size_bytes} bytes for URL {video_url}")
                    raise HTTPException(
                        status_code=413, # Payload Too Large
                        detail=f"Video file size ({int(content_length)/1024/1024:.1f} MB) exceeds limit of {settings.MAX_DOWNLOAD_SIZE_MB} MB."
                    )

                # Stream download
                downloaded_size = 0
                with open(temp_file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        downloaded_size += len(chunk)
                        # Check size limit again during streaming if Content-Length was missing
                        if not content_length and downloaded_size > max_size_bytes:
                            f.close() # Close the file before deleting
                            cleanup_files(temp_file_path) # Clean up partially downloaded file
                            logger.warning(f"Download exceeded size limit ({max_size_bytes} bytes) during streaming for URL {video_url}")
                            raise HTTPException(
                                status_code=413,
                                detail=f"Video file size exceeds limit of {settings.MAX_DOWNLOAD_SIZE_MB} MB (detected during download)."
                            )
                        f.write(chunk)

        logger.info(f"Successfully downloaded video from {video_url} ({downloaded_size/1024/1024:.2f} MB) to {temp_file_path}")
        return temp_file_path

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading {video_url}: Status {e.response.status_code}", exc_info=True)
        # Don't expose potentially sensitive remote server errors directly unless needed
        detail = f"Failed to download video. Remote server returned status {e.response.status_code}."
        if e.response.status_code == 404:
             detail = "Video URL not found (404)."
        elif 400 <= e.response.status_code < 500:
             detail = f"Could not access video URL (client error: {e.response.status_code}). Check URL permissions."
        raise HTTPException(status_code=400, detail=detail) from e # 400 Bad Request seems appropriate for client-provided URL issues
    except (httpx.RequestError, httpx.TimeoutException) as e:
        logger.error(f"Network error downloading {video_url}: {e}", exc_info=True)
        raise HTTPException(status_code=504, detail=f"Could not download video: Network error or timeout connecting to URL.") from e # 504 Gateway Timeout
    except HTTPException:
        # Re-raise HTTPExceptions from size/type checks
        raise
    except Exception as e:
        logger.error(f"Failed to download or save video from {video_url}: {e}", exc_info=True)
        cleanup_files(temp_file_path) # Attempt cleanup on unexpected errors
        raise HTTPException(status_code=500, detail=f"An internal server error occurred during video download.") from e

