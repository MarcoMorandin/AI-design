import os
import logging.config
from pathlib import Path


def setup_logging(logs_dir: str = "logs", log_level: str = None) -> None:
    """
    Configure logging for the Summarization Agent with production-ready settings.

    Args:
        logs_dir: Directory to store log files
        log_level: Override the log level (uses environment variable if not provided)
    """
    # Create logs directory if it doesn't exist
    logs_path = Path(logs_dir)
    logs_path.mkdir(exist_ok=True, parents=True)

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
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": numeric_level,
                "propagate": True,
            },
            "trento_agent_sdk": {
                "level": numeric_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "urllib3": {
                "level": "WARNING",
            },
            "httpx": {
                "level": "WARNING",
            },
            "googleapiclient": {
                "level": "WARNING",
            },
            "google.auth": {
                "level": "WARNING",
            },
            "genai": {
                "level": "INFO",
            },
        },
    }

    # Apply configuration
    logging.config.dictConfig(logging_config)

    # Log startup information
    logging.info(f"Summarization Agent logging initialized with level: {log_level}")

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


# Setup logging when the module is imported
if __name__ != "__main__":  # Don't run during imports
    if os.environ.get("INITIALIZE_LOGGING", "true").lower() in ("true", "1", "yes"):
        setup_logging()
