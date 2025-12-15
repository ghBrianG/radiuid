#!/usr/bin/env python3
"""
RadiUID Logging Configuration
Centralized logging setup with colored console output
"""

import logging
import sys
from typing import Optional

from .constants import Colors


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds color to log messages"""

    COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.MAGENTA,
    }

    def format(self, record):
        # Add color to the level name
        levelname = record.levelname
        if record.levelno in self.COLORS:
            colored_levelname = f"{self.COLORS[record.levelno]}{levelname}{Colors.BLACK}"
            record.levelname = colored_levelname

        # Format the message
        result = super().format(record)

        # Reset levelname for next use
        record.levelname = levelname

        return result


def setup_logging(
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    max_log_lines: int = 0  # Reserved for future circular logging implementation
) -> logging.Logger:
    """
    Configure logging for RadiUID

    Args:
        log_file: Path to log file (optional)
        level: Logging level (default: INFO)
        max_log_lines: Maximum lines in log file (0 = unlimited)

    Returns:
        Configured logger instance
    """
    _ = max_log_lines  # Reserved for future use
    logger = logging.getLogger('radiuid')
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            logger.error(f"Could not create log file {log_file}: {e}")

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (defaults to 'radiuid')

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'radiuid.{name}')
    return logging.getLogger('radiuid')
