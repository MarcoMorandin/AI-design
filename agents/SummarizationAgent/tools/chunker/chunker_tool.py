# filepath: /Users/marcomorandin/Desktop/AI-Design/AI-design/agents/SummarizationAgent/tools/chunker/chunker_tool.py
from .chunker_types.standardar_chuncker import chunk_document as standard_chunk
from typing import Dict, Any, Optional
import logging
import traceback
import json
import sys
import os

# Add parent directory to path to import json_utils
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from tools.json_utils import safe_json_dumps
from .core.config import settings

# Configure logging with more detailed format for production
logger = logging.getLogger(__name__)


def get_chunks(text: str, chunker_type: Optional[str] = None) -> str:
    """
    Splits a given text into smaller chunks based on the specified or configured chunker type.

    Args:
        text: The input string to be chunked. Must be a non-empty string.
        chunker_type: Optional; The type of chunker to use. If None, the
                      chunker type is determined by the application settings.

    Returns:
        A serialized JSON string containing the chunks and metadata.

    Raises:
        ValueError: If the input text is not a non-empty string.
    """

    if not text or not isinstance(text, str):
        logger.error("Invalid input: text must be a non-empty string")
        raise ValueError("Text input must be a non-empty string")

    # Use provided chunker type or fall back to settings
    selected_chunker = chunker_type or settings.CHUNCKER_TYPE

    # Log chunking operation start
    text_length = len(text)
    logger.info(
        f"Starting chunking operation using {selected_chunker} chunker on text of length: {text_length} characters"
    )

    try:
        # Choose chunking method based on configuration
        logger.info("Using standard chunking algorithm")
        chunks = standard_chunk(text)

        # Log success metrics
        chunk_count = len(chunks)
        avg_chunk_size = sum(len(chunk) for chunk in chunks) / max(chunk_count, 1)

        logger.info(
            f"Successfully created {chunk_count} chunks with {selected_chunker} chunker"
        )
        logger.debug(f"Average chunk size: {avg_chunk_size:.2f} characters")

        # Create response object
        response_data = {
            "chunks": chunks,
            "metadata": {
                "text_length": text_length,
                "chunk_count": chunk_count,
                "chunker_type": selected_chunker,
                "avg_chunk_size": avg_chunk_size,
                "success": True,
            },
        }

        # Add telemetry if metrics are enabled
        if settings.ENABLE_METRICS:
            _record_chunking_metrics(
                {
                    "text_length": text_length,
                    "chunk_count": chunk_count,
                    "chunker_type": selected_chunker,
                    "avg_chunk_size": avg_chunk_size,
                }
            )

        # Preprocess chunks to prevent escape sequence issues
        sanitized_chunks = []
        for chunk in chunks:
            # Instead of manual replacement which can introduce issues,
            # use json.dumps to handle proper escaping, then strip the quotes
            sanitized_chunk = json.dumps(chunk)[1:-1]
            sanitized_chunks.append(sanitized_chunk)

        # Update response with sanitized chunks
        response_data["chunks"] = sanitized_chunks

        # Return serialized JSON with proper handling of escape sequences
        try:
            # First attempt using our safe function
            json_response = safe_json_dumps(response_data)
            # Verify that the result is valid JSON
            json.loads(json_response)
            logger.debug("JSON serialization successful with safe_json_dumps")
            return json_response
        except Exception as e:
            logger.warning(
                f"Safe JSON dumps failed: {str(e)}, falling back to standard json.dumps"
            )
            # Fall back to direct json.dumps with ensure_ascii=False
            try:
                json_response = json.dumps(response_data, ensure_ascii=False)
                logger.debug("JSON serialization successful with fallback method")
                return json_response
            except Exception as e2:
                logger.error(f"All JSON serialization attempts failed: {str(e2)}")
                # Return a minimal valid response
                return json.dumps(
                    {
                        "chunks": ["Serialization error occurred"],
                        "metadata": {
                            "success": False,
                            "error": f"JSON serialization failed: {str(e2)}",
                        },
                    }
                )

    except Exception as e:
        logger.error(f"Error during chunking: {str(e)}")
        logger.debug(f"Exception details: {traceback.format_exc()}")

        # Fallback to simple chunking if all else fails
        logger.warning("Using emergency fallback chunking method")
        if text_length > 4000:
            logger.info(
                f"Text too large ({text_length} chars), splitting into simple chunks"
            )
            # Create basic chunks
            raw_chunks = [text[i : i + 4000] for i in range(0, text_length, 3500)]

            # Sanitize chunks to prevent escape sequence issues
            chunks = []
            for chunk in raw_chunks:
                # Use json.dumps for proper escaping of strings
                sanitized_chunk = json.dumps(chunk)[1:-1]
                chunks.append(sanitized_chunk)

            logger.info(f"Created {len(chunks)} emergency fallback chunks")

            # Create fallback response object
            fallback_response = {
                "chunks": chunks,
                "metadata": {
                    "text_length": text_length,
                    "chunk_count": len(chunks),
                    "chunker_type": "emergency_fallback",
                    "avg_chunk_size": sum(len(chunk) for chunk in chunks)
                    / max(len(chunks), 1),
                    "success": True,
                    "fallback": True,
                },
            }

            try:
                return safe_json_dumps(fallback_response)
            except Exception as e:
                logger.warning(f"Safe JSON dumps failed in fallback: {str(e)}")
                return json.dumps(fallback_response, ensure_ascii=False)
        else:
            logger.info("Text small enough to process as single chunk")

            # Sanitize the text to prevent escape sequence issues
            sanitized_text = json.dumps(text)[1:-1]

            # Create single chunk response object
            single_chunk_response = {
                "chunks": [sanitized_text],
                "metadata": {
                    "text_length": text_length,
                    "chunk_count": 1,
                    "chunker_type": "emergency_fallback",
                    "avg_chunk_size": text_length,
                    "success": True,
                    "fallback": True,
                },
            }

            try:
                return safe_json_dumps(single_chunk_response)
            except Exception as e:
                logger.warning(f"Safe JSON dumps failed in single chunk: {str(e)}")
                return json.dumps(single_chunk_response, ensure_ascii=False)


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
