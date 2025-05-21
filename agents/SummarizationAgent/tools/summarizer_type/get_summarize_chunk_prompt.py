import os
import json
import logging
import time
import ast
import sys
from openai import OpenAI
from .prompts.prompt import summary_prompt
from dotenv import load_dotenv

# Add parent directory to path to import json_utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
try:
    from json_utils import safe_json_dumps, safe_json_loads
except ImportError:
    # Fallback if json_utils is not available
    def safe_json_dumps(data):
        return json.dumps(data)

    def safe_json_loads(s, default_value=None, default=None):
        fallback = default if default is not None else default_value
        try:
            return json.loads(s)
        except Exception:
            return fallback


load_dotenv()

logger = logging.getLogger(__name__)

# Get the API key from environment variables
api_key = os.getenv("GEMINI_API_KEY")
client = OpenAI(
    api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


def parse_string_list(s: str) -> list[str] | None:
    """
    Safely parses a string representation of a list of strings
    into a Python list of strings.
    Returns None if parsing fails.
    """
    try:
        result = ast.literal_eval(s)
        if isinstance(result, list) and all(isinstance(item, str) for item in result):
            return result
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing string: {e}")
        print(f"Input string was: {s}")
        return None


def summarise_chunk(text: str, summary_type: str = "technical") -> str:
    """Summarizes a chunk of text using Gemini API.

    Available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        text (str): The text chunk to summarize.
        summary_type (str): The type of summary to generate.

    Returns:
        str: The summarized text, not just a prompt
    """
    # Get the appropriate prompt for this summary type
    prompt = summary_prompt(summary_type)

    # Create the full prompt with the input text
    full_prompt = f"""
    {prompt}
    
    --- TEXT TO SUMMARIZE ---
    {text}
    --- TEXT TO SUMMARIZE ---
    """

    # Call the Gemini API to actually summarize the text
    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "You are a math syntax expert."},
            {"role": "user", "content": full_prompt},
        ],
    )

    # Return the actual summary, not just the prompt
    return response.choices[0].message.content


def summarize_chunks(chunks_data: str, summary_type: str = "technical") -> str:
    """Summarizes text chunks from a serialized JSON object.

    Available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        chunks_data: A serialized JSON string containing the chunks and metadata,
                     as returned by the get_chunks function. Contains a "chunks" list
                     and "metadata" dictionary.
        summary_type (str): The type of summary to generate.

    Returns:
        str: A serialized JSON string containing the summaries and metadata.
    """
    # Parse the serialized JSON from get_chunks
    try:
        if not chunks_data:
            logger.error("Received empty chunks_data")
            return safe_json_dumps(
                {
                    "summaries": [],
                    "metadata": {"success": False, "error": "Received empty input"},
                }
            )

        # Log the beginning of the input for debugging
        log_preview = (
            str(chunks_data)[:100] + "..."
            if len(str(chunks_data)) > 100
            else str(chunks_data)
        )
        logger.info(f"Input preview: {log_preview}")

        if isinstance(chunks_data, dict):
            # Already a dictionary, no need to parse
            logger.info("Input is already a dictionary, using as-is")
            data = chunks_data
        else:
            # Try to parse as JSON
            logger.info("Attempting to parse input as JSON")
            try:
                # First, try direct parsing
                data = safe_json_loads(chunks_data, default=None)
                if data is None:
                    # Log more details about the content
                    logger.warning(
                        f"JSON parsing failed, input type: {type(chunks_data)}"
                    )
                    if isinstance(chunks_data, str) and len(chunks_data) > 0:
                        # Log some character codes to help diagnose escape sequence issues
                        sample_chars = [ord(c) for c in chunks_data[:20]]
                        logger.debug(f"First 20 character codes: {sample_chars}")

                        # Check for problematic escape sequences
                        problematic_sequences = [
                            "\\n",
                            "\\t",
                            "\\r",
                            '\\"',
                            "\\\\",
                            "\\/",
                            "\\b",
                            "\\f",
                        ]
                        for seq in problematic_sequences:
                            if seq in chunks_data:
                                logger.debug(f"Found problematic sequence: {seq}")

                        # Print a small sample of the content that might have issues
                        if len(chunks_data) > 1800 and len(chunks_data) < 1830:
                            logger.debug(
                                f"Content around position 1815: {chunks_data[1810:1820]}"
                            )

                    # Fall back to empty dict
                    logger.info("Falling back to empty dictionary")
                    data = {}
            except Exception as parse_error:
                logger.error(f"Exception during JSON parsing: {str(parse_error)}")
                data = {}

        chunks = data.get("chunks", [])
        metadata = data.get("metadata", {})
        logger.info(f"Successfully parsed JSON with {len(chunks)} chunks")
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(
            f"Invalid JSON input: could not parse chunks_data. Error: {str(e)}"
        )
        # Attempt to parse as a list if it's not valid JSON
        logger.info("Attempting fallback parsing methods")
        if isinstance(chunks_data, list):
            # Already a list, use directly
            logger.info("Input is already a list, using as-is")
            chunks = chunks_data
            metadata = {}
        elif isinstance(chunks_data, str):
            # Try different string parsing approaches
            if chunks_data.startswith("[") and chunks_data.endswith("]"):
                # Looks like a JSON array
                logger.info("Input appears to be a JSON array string, trying to parse")
                try:
                    chunks = json.loads(chunks_data)
                    metadata = {}
                    logger.info(
                        f"Successfully parsed as JSON array with {len(chunks)} chunks"
                    )
                except json.JSONDecodeError:
                    chunks = parse_string_list(chunks_data) or []
                    metadata = {}
                    logger.info(
                        f"Parsed using ast.literal_eval with {len(chunks)} chunks"
                    )
            else:
                # Try parsing as Python literal
                chunks = parse_string_list(chunks_data) or []
                metadata = {}
                logger.info(f"Parsed using ast.literal_eval with {len(chunks)} chunks")
        else:
            logger.error(
                f"Could not parse input in any format. Type: {type(chunks_data)}"
            )
            return safe_json_dumps(
                {
                    "summaries": [],
                    "metadata": {
                        "success": False,
                        "error": f"Invalid input format: {type(chunks_data)}",
                    },
                }
            )

    summaries = []
    start_time = time.time()

    for i, chunk in enumerate(chunks):
        logger.info(
            f"Summarizing chunk {i+1}/{len(chunks)} using {summary_type} summary type"
        )
        summary = summarise_chunk(chunk, summary_type)
        summaries.append(summary)
        logger.info(f"Chunk {i+1}: {summary}")

    # Create response object with original metadata plus summary information
    processing_time = time.time() - start_time
    response_data = {
        "summaries": summaries,
        "metadata": {
            **metadata,
            "summary_type": summary_type,
            "summary_count": len(summaries),
            "processing_time_seconds": round(processing_time, 2),
            "success": True,
        },
    }

    # Return serialized JSON
    try:
        json_response = safe_json_dumps(response_data)
        logger.info(f"Successfully serialized response with {len(summaries)} summaries")
        return json_response
    except Exception as e:
        logger.error(f"Error serializing response to JSON: {str(e)}")
        # Return a simplified response
        return safe_json_dumps(
            {
                "summaries": [
                    str(s) for s in summaries
                ],  # Convert to strings to ensure serialization
                "metadata": {
                    "summary_count": len(summaries),
                    "success": True,
                    "warning": "JSON serialization issue with full response, returning simplified version",
                },
            }
        )
