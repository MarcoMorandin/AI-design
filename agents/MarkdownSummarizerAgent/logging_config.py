import os
import logging.config
from pathlib import Path


def setup_logging(logs_dir: str = "logs", log_level: str = None) -> None:
    """
    Configure logging for the application with production-ready settings.

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
            "json": {
                "format": '{"timestamp":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","msg":%(message)s}',
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "standard",
            },
            "file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": logs_path / "app.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
                "formatter": "standard",
            },
            "error_file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": logs_path / "error.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
                "formatter": "standard",
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file", "error_file"],
                "level": numeric_level,
                "propagate": True,
            },
        },
    }

    # Apply the configuration
    logging.config.dictConfig(logging_config)
    logging.info(f"Logging initialized at level {log_level}")
