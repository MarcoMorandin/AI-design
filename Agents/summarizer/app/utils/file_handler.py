
import fitz  # PyMuPDF
import camelot
import pdfplumber
from docx import Document
from typing import Dict, Any
import logging
import zipfile  # Importato per estrarre i file da un DOCX (che è un file ZIP)
from pathlib import Path
from app.core.config import settings
from typing import List, Tuple, Union
import easyocr
import certifi

reader = easyocr.Reader(['en', 'it'])
OCR_AVAILABLE = True

import uuid
from pathlib import Path
import httpx
from fastapi import HTTPException
# Ensure that your settings, logger, and any cleanup utility functions (like cleanup_files) are properly imported.
# Example:
# from your_project import settings, logger, cleanup_files
logger = logging.getLogger(__name__)
logging.getLogger("pdfminer").setLevel(logging.ERROR)


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
            

async def download_document_from_url(pdf_url: str) -> Path:
    """Downloads a PDF from a URL to a temporary file."""
    request_id = uuid.uuid4()
    # Check for a .pdf extension; default to .pdf if not found or if the extension isn't valid.
    suffix = Path(pdf_url).suffix.lower() if Path(pdf_url).suffix.lower() == ".pdf" else ".pdf"
    
    temp_file_path = settings.TEMP_DIR / f"{request_id}_downloaded{suffix}"
    logger.info(f"Attempting to download document from {pdf_url} to {temp_file_path}")

    download_timeout = httpx.Timeout(settings.DOWNLOAD_TIMEOUT, connect=settings.DOWNLOAD_TIMEOUT)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

    try:
        async with httpx.AsyncClient(timeout=download_timeout, limits=limits, follow_redirects=True, verify=certifi.where()) as client:
            async with client.stream("GET", pdf_url) as response:
                # Raise an exception for bad status codes (4xx or 5xx)
                response.raise_for_status()

                # Optional: Check Content-Type to ensure it's a PDF
                content_type = response.headers.get("content-type", "").lower()
                # Use a list of allowed PDF MIME types. This could be defined in your settings.
                #allowed_pdf_types = getattr(settings, "ALLOWED_PDF_CONTENT_TYPES", ["application/pdf"])
                if settings.ALLOWED_DOCUMENT_CONTENT_TYPES and not any(allowed_type in content_type for allowed_type in settings.ALLOWED_DOCUMENT_CONTENT_TYPES):
                    # Allow a generic stream (e.g., application/octet-stream) as a fallback.
                    if content_type != "application/octet-stream":
                        logger.warning(f"Disallowed content-type '{content_type}' for URL {pdf_url}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported content type: {content_type}. Allowed types: {allowed_pdf_types}"
                        )
                    else:
                        logger.warning(f"Generic content-type '{content_type}', proceeding with download for URL {pdf_url}")

                # Optional: Check Content-Length for file size limits.
                content_length = response.headers.get("content-length")
                max_size_bytes = settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024  # Convert MB to bytes
                if content_length and int(content_length) > max_size_bytes:
                    logger.warning(f"Content-Length {content_length} exceeds limit of {max_size_bytes} bytes for URL {pdf_url}")
                    raise HTTPException(
                        status_code=413,  # Payload Too Large
                        detail=f"PDF file size ({int(content_length) / 1024 / 1024:.1f} MB) exceeds limit of {settings.MAX_DOWNLOAD_SIZE_MB} MB."
                    )

                # Stream the download to a file.
                downloaded_size = 0
                with open(temp_file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        downloaded_size += len(chunk)
                        # If no Content-Length header, check the file size on the fly.
                        if not content_length and downloaded_size > max_size_bytes:
                            f.close()  # Ensure the file is closed before cleaning up.
                            cleanup_files(temp_file_path)  # Clean up the partial file.
                            logger.warning(f"Download exceeded size limit ({max_size_bytes} bytes) during streaming for URL {pdf_url}")
                            raise HTTPException(
                                status_code=413,
                                detail=f"PDF file size exceeds limit of {settings.MAX_DOWNLOAD_SIZE_MB} MB (detected during download)."
                            )
                        f.write(chunk)

        logger.info(f"Successfully downloaded PDF from {pdf_url} ({downloaded_size / 1024 / 1024:.2f} MB) to {temp_file_path}")
        return temp_file_path

    except httpx.HTTPError as http_err:
        logger.error(f"HTTP error occurred during PDF download: {http_err}")
        raise HTTPException(status_code=400, detail=str(http_err))
    except Exception as err:
        logger.error(f"Unexpected error occurred during PDF download: {err}")
        cleanup_files(temp_file_path) # Attempt cleanup on unexpected errors
        raise HTTPException(status_code=500, detail="An unexpected error occurred while downloading the PDF.")