from .chunker_types.standardar_chuncker import chunk_document as standard_chunk
from typing import List, Optional, Dict, Any
import logging
import time
import traceback
from .core.config import settings

# Configure logging with more detailed format for production
logger = logging.getLogger(__name__)


def get_chunks(text: str, chunker_type: Optional[str] = None) -> List[str]:
    """
    Splits input text into chunks using the specified algorithm.

    Args:
        text (str): The input text to be chunked.
        chunker_type (Optional[str]): The type of chunker to use ('standard' or 'cosine').
                                     If None, uses the value from settings.

    Returns:
        List[str]: A list of text chunks.

    Raises:
        ValueError: If the text is invalid or chunking fails completely.
    """
    if not text or not isinstance(text, str):
        logger.error("Invalid input: text must be a non-empty string")
        raise ValueError("Text input must be a non-empty string")

    # Use provided chunker type or fall back to settings
    selected_chunker = chunker_type or settings.CHUNCKER_TYPE

    # Log chunking operation start
    start_time = time.time()
    text_length = len(text)
    logger.info(
        f"Starting chunking operation using {selected_chunker} chunker on text of length: {text_length} characters"
    )

    try:
        # Choose chunking method based on configuration
        logger.info("Using standard chunking algorithm")
        chunks = standard_chunk(text)

        # Log success metrics
        processing_time = time.time() - start_time
        chunk_count = len(chunks)
        avg_chunk_size = sum(len(chunk) for chunk in chunks) / max(chunk_count, 1)

        logger.info(
            f"Successfully created {chunk_count} chunks in {processing_time:.2f} seconds"
        )
        logger.debug(f"Average chunk size: {avg_chunk_size:.2f} characters")

        # Add telemetry if metrics are enabled
        if settings.ENABLE_METRICS:
            _record_chunking_metrics(
                {
                    "text_length": text_length,
                    "chunk_count": chunk_count,
                    "chunker_type": selected_chunker,
                    "processing_time": processing_time,
                    "avg_chunk_size": avg_chunk_size,
                }
            )

        return chunks

    except Exception as e:
        logger.error(f"Error during chunking: {str(e)}")
        logger.debug(f"Exception details: {traceback.format_exc()}")

        # Fallback to simple chunking if all else fails
        logger.warning("Using emergency fallback chunking method")
        if text_length > 4000:
            logger.info(
                f"Text too large ({text_length} chars), splitting into simple chunks"
            )
            chunks = [text[i : i + 4000] for i in range(0, text_length, 3500)]
            logger.info(f"Created {len(chunks)} emergency fallback chunks")
            return chunks
        else:
            logger.info("Text small enough to process as single chunk")
            return [text]


def _record_chunking_metrics(metrics: Dict[str, Any]) -> None:
    """
    Record metrics about the chunking process for monitoring in production.
    This is a placeholder for actual metrics recording (e.g., Prometheus, CloudWatch).

    Args:
        metrics: Dictionary of metrics to record
    """
    # In a production environment, this would send metrics to a monitoring system
    # For now, just log them in debug mode
    logger.debug(f"Chunking metrics: {metrics}")
