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
            try:
                # More reliable method: use base64 encoding to avoid escape sequence issues
                import base64

                # Encode the string to bytes, then encode to base64, then decode to string
                encoded = base64.b64encode(chunk.encode("utf-8")).decode("ascii")
                sanitized_chunks.append(
                    {
                        "content": chunk,  # Original content (for tools that can handle it)
                        "encoding": "none",  # Indicate this is unencoded
                        "encoded_content": encoded,  # Base64 encoded content
                        "encoding_type": "base64",  # Indicate the encoding type
                    }
                )
            except Exception as chunk_encode_error:
                logger.warning(f"Error encoding chunk: {str(chunk_encode_error)}")
                # Fall back to simpler approach
                sanitized_chunks.append(
                    {
                        "content": chunk,
                        "encoding": "none",
                        "encoded_content": "",
                        "encoding_type": "none",
                    }
                )

        # Update response with sanitized chunks
        response_data["chunks"] = sanitized_chunks
        response_data["metadata"]["content_encoding"] = "wrapped_with_base64_option"

        # Return serialized JSON with proper handling of escape sequences
        try:
            # Ensure response_data is a dictionary before dumping
            if not isinstance(response_data, dict):
                logger.error(f"response_data is not a dict: {type(response_data)}")
                # Create a minimal error dict to dump
                response_data = {
                    "chunks": ["Error: Internal data preparation failed."],
                    "metadata": {
                        "success": False,
                        "error": "Internal data preparation failed before JSON serialization",
                    },
                }

            # json.dumps should handle escaping correctly. ensure_ascii=False is good for unicode.
            json_response = json.dumps(response_data, ensure_ascii=False)
            # Basic validation that it's loadable (optional, json.dumps should be reliable)
            # json.loads(json_response)
            logger.debug("JSON serialization successful with standard json.dumps")
            return json_response
        except (
            TypeError
        ) as te:  # Catch TypeError which can happen if data isn't serializable
            logger.error(
                f"TypeError during JSON serialization in get_chunks: {str(te)}. Data: {response_data}",
                exc_info=True,
            )
            return json.dumps(
                {
                    "chunks": [
                        "Serialization error occurred due to unsendable data type"
                    ],
                    "metadata": {
                        "success": False,
                        "error": f"JSON serialization failed (TypeError): {str(te)}",
                    },
                }
            )
        except Exception as e:
            logger.error(
                f"All JSON serialization attempts failed in get_chunks: {str(e)}",
                exc_info=True,
            )
            # Return a minimal valid response
            return json.dumps(
                {
                    "chunks": ["Serialization error occurred"],
                    "metadata": {
                        "success": False,
                        "error": f"JSON serialization failed: {str(e)}",
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
