import logging
import os
import sys
from logging.handlers import RotatingFileHandler


# Set up logging
def setup_logging(log_level=logging.INFO):

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Log format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific loggers to WARNING to reduce noise
    for logger_name in ["httpx", "urllib3", "asyncio", "aiohttpx"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# Initialize logging
setup_logging()
