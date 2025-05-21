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
    logger.info(f"summarize_chunks received input of type: {type(chunks_data)}")
    if isinstance(chunks_data, str):
        logger.debug(
            f"summarize_chunks received string input (first 500 chars): {chunks_data[:500]}"
        )
    else:
        logger.warning(f"summarize_chunks received non-string input: {chunks_data}")
        # Attempt to dump it to a string if it's a dict/list,
        # though ideally it should always be a string from the agent
        try:
            chunks_data = json.dumps(chunks_data)
            logger.info("Converted non-string input to JSON string for processing.")
        except Exception as e:
            logger.error(f"Could not convert input to JSON string: {e}")
            error_response = {
                "summaries": [],
                "metadata": {
                    "success": False,
                    "error": "Invalid input type, not a string or serializable.",
                },
            }
            return json.dumps(error_response)

    if not chunks_data:
        logger.error("Received empty chunks_data string")
        return json.dumps(  # Use json.dumps, not safe_json_dumps if it's a custom one
            {
                "summaries": [],
                "metadata": {"success": False, "error": "Received empty input string"},
            }
        )

    try:
        data = json.loads(chunks_data)  # Strict JSON parsing
        logger.info("Successfully parsed chunks_data JSON string.")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input for chunks_data: {e}")
        logger.error(f"Problematic JSON string: {chunks_data}")
        return json.dumps(  # Use json.dumps
            {
                "summaries": [],
                "metadata": {
                    "success": False,
                    "error": "Invalid JSON format for input chunks_data.",
                    "details": str(e),
                    "received_input_preview": chunks_data[:200],  # Log a preview
                },
            }
        )

    chunks_list_from_json = data.get(
        "chunks", []
    )  # Expecting 'chunks' key from get_chunks output
    metadata = data.get("metadata", {})

    is_encoded = metadata.get("content_encoding") == "wrapped_with_base64_option"

    processed_chunks_content = []
    if isinstance(chunks_list_from_json, list):
        for i, chunk_item in enumerate(chunks_list_from_json):
            if isinstance(
                chunk_item, dict
            ):  # This is the expected structure from your chunker
                if (
                    is_encoded
                    and chunk_item.get("encoding_type") == "base64"
                    and chunk_item.get("encoded_content")
                ):
                    try:
                        import base64

                        decoded_content = base64.b64decode(
                            chunk_item["encoded_content"].encode("ascii")
                        ).decode("utf-8")
                        processed_chunks_content.append(decoded_content)
                    except Exception as decode_error:
                        logger.warning(
                            f"Error decoding chunk {i}: {str(decode_error)}, falling back to 'content'"
                        )
                        processed_chunks_content.append(
                            chunk_item.get("content", "Error decoding chunk")
                        )
                else:
                    processed_chunks_content.append(
                        chunk_item.get("content", f"Missing content for chunk {i}")
                    )
            elif isinstance(
                chunk_item, str
            ):  # Fallback if chunks are just strings (not ideal based on your chunker)
                logger.warning(
                    f"Chunk {i} is a plain string, not a dict. This might indicate an issue upstream."
                )
                processed_chunks_content.append(chunk_item)
            else:
                logger.warning(
                    f"Unexpected item type in chunks list at index {i}: {type(chunk_item)}"
                )
                processed_chunks_content.append(f"Invalid chunk item at index {i}")
    else:
        logger.error(
            f"Parsed 'chunks' field is not a list. Found: {type(chunks_list_from_json)}"
        )
        return json.dumps(
            {
                "summaries": [],
                "metadata": {
                    **metadata,
                    "success": False,
                    "error": "Chunks data is not a list.",
                },
            }
        )

    summaries = []
    start_time = time.time()

    for i, text_chunk_content in enumerate(processed_chunks_content):
        logger.info(
            f"Summarizing chunk {i+1}/{len(processed_chunks_content)} using {summary_type} summary type"
        )
        summary = summarise_chunk(
            text_chunk_content, summary_type
        )  # summarise_chunk expects plain text
        summaries.append(summary)

    processing_time = time.time() - start_time
    response_data = {
        "summaries": summaries,  # This is a list of strings
        "metadata": {
            **metadata,  # Carry over metadata from chunking
            "original_chunk_count": len(processed_chunks_content),
            "summary_type": summary_type,
            "summary_count": len(summaries),
            "processing_time_seconds": round(processing_time, 2),
            "success": True,
        },
    }

    try:
        return json.dumps(response_data)  # Ensure output is a valid JSON string
    except Exception as e:
        logger.error(
            f"Error serializing response to JSON in summarize_chunks: {str(e)}"
        )
        # Simplified error response
        return json.dumps(
            {
                "summaries": ["Error during final serialization."],
                "metadata": {
                    "success": False,
                    "error": "Could not serialize final response.",
                },
            }
        )
