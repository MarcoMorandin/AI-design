import os
import json
import logging
import ast
import sys
from openai import OpenAI
from .prompts.prompt import generate_final_summary
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
        else:
            print(f"Warning: Parsed result is not a list of strings: {type(result)}")
            return None  # Or raise a custom error
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing string: {e}")
        print(f"Input string was: {s}")
        return None


def combine_chunk_summaries(
    summaries_data: str, summary_type: str = "technical"
) -> str:
    """Creates a final summary from serialized JSON containing chunk summaries using Gemini API.

    Available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        summaries_data (str): A serialized JSON string containing summaries and metadata,
                             as returned by the summarize_chunks function.
        summary_type (str): The type of summary to generate.

    Returns:
        str: The final combined summary.
    """
    # Parse the serialized JSON from summarize_chunks
    try:
        logger.info(f"Received summaries_data type: {type(summaries_data)}")
        if not summaries_data:
            logger.error("Received empty summaries_data")
            return "Error: Received empty input"

        # Log the beginning of the input for debugging
        log_preview = (
            str(summaries_data)[:100] + "..."
            if len(str(summaries_data)) > 100
            else str(summaries_data)
        )
        logger.info(f"Input preview: {log_preview}")

        if isinstance(summaries_data, dict):
            # Already a dictionary, no need to parse
            logger.info("Input is already a dictionary, using as-is")
            data = summaries_data
        else:
            # Try to parse as JSON
            logger.info("Attempting to parse input as JSON")
            try:
                # First, try direct parsing
                data = safe_json_loads(summaries_data, default=None)
                if data is None:
                    # Log more details about the content
                    logger.warning(
                        f"JSON parsing failed, input type: {type(summaries_data)}"
                    )
                    if isinstance(summaries_data, str) and len(summaries_data) > 0:
                        # Log some character codes to help diagnose escape sequence issues
                        sample_chars = [ord(c) for c in summaries_data[:20]]
                        logger.debug(f"First 20 character codes: {sample_chars}")

                    # Fall back to empty dict
                    logger.info("Falling back to empty dictionary")
                    data = {}
            except Exception as parse_error:
                logger.error(f"Exception during JSON parsing: {str(parse_error)}")
                data = {}

        # Extract summaries from the data
        if isinstance(data, dict) and "summaries" in data:
            summaries = data["summaries"]
            # We can use metadata later if needed
        else:
            # If not a properly formatted JSON with summaries
            if isinstance(data, list):
                summaries = data
                logger.info("Using data as list of summaries")
            else:
                # Try to parse as string list
                logger.warning(
                    f"Unexpected JSON structure, trying fallback parsing. Data type: {type(data)}"
                )
                summaries = parse_string_list(str(summaries_data))
                if not summaries:
                    logger.error("Could not parse input as summaries list")
                    # Instead of immediately returning an error, provide a fallback
                    logger.info("Using a fallback empty summary list")
                    summaries = []
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        # Attempt to parse directly as a list
        try:
            if isinstance(summaries_data, list):
                logger.info("Input is already a list, using as-is")
                summaries = summaries_data
            elif isinstance(summaries_data, str):
                logger.info("Attempting to parse string input as a list")
                if summaries_data.startswith("[") and summaries_data.endswith("]"):
                    try:
                        # Try parsing as JSON array
                        summaries = json.loads(summaries_data)
                        logger.info(
                            f"Successfully parsed as JSON array with {len(summaries)} items"
                        )
                    except json.JSONDecodeError:
                        # Try literal eval
                        summaries = parse_string_list(summaries_data)
                        if summaries:
                            logger.info(
                                f"Successfully parsed as literal with {len(summaries)} items"
                            )
                else:
                    summaries = parse_string_list(summaries_data)

                if not summaries:
                    logger.error("Could not parse input as summaries list")
                    # Instead of immediately returning an error, provide a fallback
                    logger.info("Using a fallback empty summary list")
                    summaries = []
            else:
                logger.error(f"Unsupported input type: {type(summaries_data)}")
                # Instead of immediately returning an error, provide a fallback
                summaries = []
        except Exception as e:
            logger.error(f"Error parsing summaries data: {str(e)}")
            # Instead of immediately returning an error, provide a fallback
            summaries = []

    if not isinstance(summaries, list):
        summaries = parse_string_list(summaries)

    logger.info(f"type{type(summaries)} content: {summaries}")

    # Handle the case of empty summaries list
    if not summaries:
        logger.warning("Empty summaries list, providing a fallback summary")
        return "The document could not be summarized due to processing errors. Please try again with a different document or format."

    # Join the summaries with a newline and a separator
    combined_text = "\n\n--- SUMMARY CHUNK ---\n\n".join(summaries)

    # Get the appropriate prompt for this summary type and situation
    # We're combining multiple summaries, so text_was_splitted is True
    prompt = generate_final_summary(summary_type, text_was_splitted=True)

    # Create the full prompt with the combined summaries
    full_prompt = f"""
    {prompt}
    
    {combined_text}
    """

    # Call the Gemini API to actually create the final summary
    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "You are a math syntax expert."},
            {"role": "user", "content": full_prompt},
        ],
    )

    # Return the actual final summary, not just the prompt
    return response.choices[0].message.content
