import json
import logging

logger = logging.getLogger(__name__)


def safe_json_dumps(data, default_msg="Error serializing to JSON"):
    """
    Safely serialize Python data structure to JSON string.

    Args:
        data: The Python data structure to serialize
        default_msg: Default message to include in emergency response

    Returns:
        str: A JSON string
    """
    try:
        # Try to serialize the data with ensure_ascii=False to handle unicode
        # and escape special characters to ensure valid JSON
        result = json.dumps(data, ensure_ascii=False, default=str)
        # Verify the result can be parsed back
        json.loads(result)
        return result
    except (TypeError, ValueError, OverflowError) as e:
        logger.error(f"JSON serialization error: {str(e)}")

        # Create safe emergency response
        try:
            # Convert non-serializable data to strings
            if isinstance(data, dict):
                # For dictionaries, try to convert problematic values to strings
                safe_data = {}
                for k, v in data.items():
                    try:
                        # Test if this key-value pair is serializable
                        json.dumps({k: v})
                        safe_data[k] = v
                    except (TypeError, ValueError, OverflowError):
                        # If not, convert to string
                        safe_data[k] = str(v)

                return json.dumps(safe_data)

            elif isinstance(data, list):
                # For lists, convert each element that causes problems
                safe_data = []
                for item in data:
                    try:
                        # Check if item is serializable
                        json.dumps(item)
                        safe_data.append(item)
                    except (TypeError, ValueError, OverflowError):
                        safe_data.append(str(item))

                return json.dumps(safe_data)

            else:
                # For other types, return a simple error response
                return json.dumps({"error": default_msg, "details": str(e)})

        except Exception as final_e:
            # If all else fails, return a minimal valid JSON string
            logger.error(f"Emergency JSON serialization also failed: {str(final_e)}")
            return json.dumps({"error": default_msg})


def safe_json_loads(json_str, default_value=None, default=None):
    """
    Safely parse a JSON string into a Python data structure.

    Args:
        json_str: The JSON string to parse
        default_value: Value to return if parsing fails
        default: Alternative parameter name for default_value (for backward compatibility)

    Returns:
        The parsed Python data structure or default_value if parsing fails
    """
    # Use default if provided, otherwise use default_value
    fallback = default if default is not None else default_value

    if not json_str:
        logger.warning("Empty JSON string provided to safe_json_loads")
        return fallback

    # If it's already a dict or list, no need to parse
    if isinstance(json_str, (dict, list)):
        return json_str

    # Ensure we're working with a string
    if not isinstance(json_str, str):
        try:
            json_str = str(json_str)
        except Exception as e:
            logger.error(f"Could not convert input to string: {str(e)}")
            return fallback

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")

        # Log the exact character causing the issue, if possible
        if "Invalid \\escape" in str(e) and hasattr(e, "pos"):
            pos = e.pos
            context_start = max(0, pos - 10)
            context_end = min(len(json_str), pos + 10)
            context = json_str[context_start:context_end]
            logger.warning(f"Invalid escape sequence near: '{context}', position {pos}")

            # Try a very specific fix for invalid escape sequences
            try:
                # In case of invalid escape: directly sanitize the string by replacing backslashes
                # with double backslashes before re-encoding as JSON
                sanitized_str = json_str.replace("\\", "\\\\")
                # Now replace any double backslashes that were already proper (\\\\) with just \\
                sanitized_str = sanitized_str.replace("\\\\\\\\", "\\\\")
                # Then fix properly escaped quotes
                sanitized_str = sanitized_str.replace('\\\\"', '\\"')

                logger.info("Attempting to parse with fully sanitized string")
                return json.loads(sanitized_str)
            except json.JSONDecodeError:
                logger.warning("Sanitized string fix attempt failed")

        # Try to fix common issues with escape sequences
        try:
            # Fix common escape sequence issues
            fixed_str = json_str.replace("\\\\", "\\").replace('\\"', '"')
            logger.info("Attempting to parse with fixed escape sequences")
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            logger.warning("First fix attempt failed, trying more aggressive fixes")

        try:
            # More aggressive fix: replace all problematic backslashes
            import re

            # Replace invalid escapes with their literal representation
            fixed_str = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", json_str)
            logger.info("Attempting to parse with regex-fixed escape sequences")
            return json.loads(fixed_str)
        except (json.JSONDecodeError, re.error) as e:
            logger.error(f"All JSON parsing fix attempts failed: {str(e)}")

            # Last ditch effort: try to extract and reformat the JSON structure
            try:
                logger.info("Attempting extreme recovery of JSON structure")

                # Try to recreate the JSON structure
                if json_str.startswith("{") and json_str.endswith("}"):
                    # It's a dictionary format, attempt to manually extract key-value pairs
                    # by recreating a clean dictionary and using json.dumps to properly escape
                    import ast

                    # Extract keys and values more safely
                    reconstructed_dict = {}

                    # Try to extract as eval-able Python dictionary
                    try:
                        # Convert to a Python literal if possible
                        reconstructed_dict = ast.literal_eval(json_str)
                        logger.info(
                            "Successfully reconstructed JSON using literal_eval"
                        )
                    except (SyntaxError, ValueError):
                        logger.warning(
                            "ast.literal_eval failed, trying manual reconstruction"
                        )
                        # Fall back to manual reconstruction if that fails
                        try:
                            # Crude method to handle nested structures by replacing with placeholders
                            # then parsing top-level structure
                            placeholder_str = re.sub(
                                r"[\[\{].*?[\]\}]", '"placeholder"', json_str
                            )
                            placeholder_str = re.sub(
                                r'".*?"', '"placeholder"', placeholder_str
                            )
                            placeholder_str = re.sub(r"\\", "", placeholder_str)

                            # Extract keys
                            key_matches = re.findall(r'"([^"]+)"\s*:', placeholder_str)
                            for key in key_matches:
                                reconstructed_dict[key] = "Value could not be recovered"

                            logger.info(
                                f"Manually reconstructed keys: {list(reconstructed_dict.keys())}"
                            )
                        except Exception as e:
                            logger.error(f"Manual key extraction failed: {str(e)}")

                    # Create a clean JSON string
                    clean_json = json.dumps(reconstructed_dict)
                    return json.loads(clean_json)

                elif json_str.startswith("[") and json_str.endswith("]"):
                    # Try to extract list items safely
                    try:
                        # Simple case: if it's just a list of strings with issues, create dummy list
                        item_count = json_str.count(",") + 1
                        dummy_list = ["Item could not be recovered"] * item_count
                        logger.info(
                            f"Created fallback list with {item_count} placeholder items"
                        )
                        return dummy_list
                    except Exception as e:
                        logger.error(f"List reconstruction failed: {str(e)}")

            except Exception as final_e:
                logger.error(f"Extreme JSON recovery also failed: {str(final_e)}")

            return fallback
    except TypeError as e:
        logger.error(f"Type error in JSON parsing: {str(e)}")
        return fallback
