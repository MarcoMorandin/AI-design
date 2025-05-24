from typing import List
from ..core.config import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)


def chunk_document(text: str) -> List[str]:
    """
    Divides document text into manageable chunks for processing,
    with configurable overlap between chunks based on settings.OVERLAPP_CHUNK.

    Args:
        text (str): Complete document text to be chunked.

    Returns:
        List[str]: A list of text chunks.

    Raises:
        ValueError: If text is None or empty.
    """
    if text is None or not isinstance(text, str):
        logger.error("Invalid text input: text cannot be None and must be a string")
        raise ValueError("Text input must be a non-empty string")

    if not text.strip():
        logger.warning("Empty text provided for chunking")
        return []

    chunks = []
    text_length = len(text)

    logger.debug(f"Chunking text of {text_length} characters using standard chunker")
    logger.debug(
        f"Max chunk size: {settings.MAX_LENGTH_PER_CHUNK}, Overlap: {settings.OVERLAPP_CHUNK}"
    )

    # If text is shorter than maximum chunk size, return it as a single chunk
    if text_length < settings.MAX_LENGTH_PER_CHUNK:
        logger.debug(
            f"Text length ({text_length}) less than max chunk size, returning as single chunk"
        )
        chunks.append(text)
        return chunks

    start = 0
    chunk_count = 0

    try:
        while start < text_length:
            # Calculate end position for current chunk
            end = min(start + settings.MAX_LENGTH_PER_CHUNK, text_length)

            # Add current chunk to list
            current_chunk = text[start:end]
            chunks.append(current_chunk)
            chunk_count += 1

            # Move start position for next chunk, accounting for overlap
            start += settings.MAX_LENGTH_PER_CHUNK - settings.OVERLAPP_CHUNK

            # Break if we've reached the end of text
            if end == text_length:
                break

        logger.info(f"Successfully created {chunk_count} chunks with standard chunker")
        return chunks

    except Exception as e:
        logger.error(f"Error in standard chunking process: {str(e)}")
        # Fallback to a simpler chunking method
        logger.warning("Using fallback chunking method")
        return _fallback_chunking(text)


def _fallback_chunking(text: str) -> List[str]:
    """
    Simple fallback chunking method when the main chunking method fails.
    Divides text into simple fixed-size chunks with minimal overlap.

    Args:
        text (str): Text to chunk.

    Returns:
        List[str]: A list of text chunks.
    """
    chunk_size = min(settings.MAX_LENGTH_PER_CHUNK, 4000)
    overlap = min(settings.OVERLAPP_CHUNK, 200)
    chunks = []

    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i : i + chunk_size])

    return chunks
