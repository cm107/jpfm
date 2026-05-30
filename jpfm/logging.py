"""
Logging configuration for JPFM application.

This module provides a centralized logging factory using Python's standard
logging module, with support for console and file output.
"""

import logging
import logging.handlers
from pathlib import Path


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create or retrieve a logger instance with configured handlers.

    This function returns a logger with both console and file handlers.
    Logs are written to storage/logs/ directory.

    Args:
        name: Logger name (typically __name__ of calling module).
        level: Logging level (default: logging.INFO).

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if logger.hasHandlers():
        return logger

    # Create storage/logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "storage" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file = log_dir / f"{name.replace('.', '_')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10_000_000, backupCount=5  # 10MB, 5 backups
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger
