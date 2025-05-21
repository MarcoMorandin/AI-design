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
) -> str:  # This function should return the FINAL TEXT SUMMARY, not a JSON string.
    logger.info(
        f"combine_chunk_summaries received input of type: {type(summaries_data)}"
    )
    if isinstance(summaries_data, str):
        logger.debug(
            f"combine_chunk_summaries received string input (first 500 chars): {summaries_data[:500]}"
        )
    else:
        logger.warning(
            f"combine_chunk_summaries received non-string input: {summaries_data}"
        )
        # Attempt to dump it to a string
        try:
            summaries_data = json.dumps(summaries_data)
            logger.info("Converted non-string input to JSON string for processing.")
        except Exception as e:
            logger.error(f"Could not convert input to JSON string: {e}")
            return "Error: Invalid input type to combine_chunk_summaries, not a string or serializable."

    if not summaries_data:
        logger.error("Received empty summaries_data string")
        return "Error: Received empty input string for summaries."

    try:
        data = json.loads(summaries_data)  # Strict JSON parsing
        logger.info("Successfully parsed summaries_data JSON.")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input for summaries_data: {e}")
        logger.error(f"Problematic JSON string: {summaries_data}")
        # This function returns the final summary string, so error message should be a string.
        return f"Error: Invalid JSON format for input summaries_data. Details: {str(e)}. Input preview: {summaries_data[:200]}"

    summaries_list = data.get(
        "summaries", []
    )  # Expecting 'summaries' key from summarize_chunks output

    if not isinstance(summaries_list, list) or not all(
        isinstance(s, str) for s in summaries_list
    ):
        logger.error(
            f"Parsed 'summaries' field is not a list of strings. Found: {type(summaries_list)}"
        )
        # Try to coerce, but log heavily
        if isinstance(summaries_list, list):
            summaries_list = [str(item) for item in summaries_list]
            logger.warning("Coerced items in summaries list to string.")
        else:
            return "Error: Summaries data after JSON parsing is not a list of strings."

    if not summaries_list:
        logger.warning("Received an empty list of summaries.")
        return "No summaries were generated from the provided content chunks."

    # Join the summaries with a newline and a separator
    combined_text = "\n\n--- SUMMARY CHUNK ---\n\n".join(summaries_list)
    logger.info(
        f"Combined {len(summaries_list)} summaries into text of length {len(combined_text)}."
    )

    prompt = generate_final_summary(summary_type, text_was_splitted=True)
    full_prompt = f"{prompt}\n\n{combined_text}"

    try:
        response = client.chat.completions.create(
            model="gemini-2.0-flash",  # Consider using a more capable model for final combination if quality is an issue
            messages=[
                {
                    "role": "system",
                    "content": "You are a math syntax expert and a proficient summarizer.",
                },
                {"role": "user", "content": full_prompt},
            ],
        )
        final_summary = response.choices[0].message.content
        logger.info("Successfully generated final combined summary.")
        return final_summary
    except Exception as e:
        logger.error(
            f"Error calling LLM for final summary combination: {e}", exc_info=True
        )
        return f"Error: Could not generate the final summary from combined chunks. LLM API call failed. Details: {str(e)}"
