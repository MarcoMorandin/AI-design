import os
import logging.config
import json
from typing import Any


def truncate_string(s: str, max_length: int = 50) -> str:
    """Truncate a string to max_length characters, adding ellipsis if needed."""
    if len(s) <= max_length:
        return s
    return s[: max_length - 3] + "..."


def safe_json_serialize(obj: Any, max_length: int = 50) -> str:
    """
    Convert a complex object to a JSON string, handling errors and truncating if needed.

    Args:
        obj: The object to serialize
        max_length: Maximum length of the returned string

    Returns:
        A truncated, serialized representation of the object
    """
    try:
        if isinstance(obj, str):
            return truncate_string(obj, max_length)
        elif isinstance(obj, (dict, list, int, float, bool, type(None))):
            result = json.dumps(obj, ensure_ascii=False)
            return truncate_string(result, max_length)
        elif hasattr(obj, "_dict_") or hasattr(obj, "__dict__"):
            if hasattr(obj, "_dict_"):
                result = json.dumps(obj._dict_, ensure_ascii=False)
            else:
                result = json.dumps(obj.__dict__, ensure_ascii=False)
            return truncate_string(result, max_length)
        else:
            return truncate_string(str(obj), max_length)
    except Exception:
        return truncate_string(str(obj), max_length)


def setup_logging(logs_dir: str = "logs", log_level: str = None) -> None:
    """
    Configure logging for the Trento Agent SDK with production-ready settings.

    Args:
        logs_dir: Directory to store log files
        log_level: Override the log level (uses environment variable if not provided)
    """

    # Get log level from environment or use INFO as default
    log_level = log_level or os.environ.get("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Define logging configuration dictionary
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "standard",
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": numeric_level,
                "propagate": True,
            },
            "trento_agent_sdk": {
                "handlers": ["console"],
                "level": numeric_level,
                "propagate": False,
            },
            "trento_agent_sdk.tool": {
                "handlers": ["console"],
                "level": numeric_level,
                "propagate": False,
            },
            "urllib3": {
                "level": "WARNING",
            },
            "httpx": {
                "level": "WARNING",
            },
            "uvicorn": {
                "level": "WARNING",
            },
            "fastapi": {
                "level": "WARNING",
            },
        },
    }

    # Apply configuration
    logging.config.dictConfig(logging_config)

    # Log startup information
    logging.getLogger("trento_agent_sdk").info(
        f"Trento Agent SDK logging initialized with level: {log_level}"
    )

    # Set JSON formatter for production environment
    if os.environ.get("ENVIRONMENT") == "production":
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(
                    logging.Formatter(
                        fmt="%(asctime)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )


# Initialize logging when module is imported
if os.environ.get("INITIALIZE_LOGGING", "true").lower() in ("true", "1", "yes"):
    setup_logging()
