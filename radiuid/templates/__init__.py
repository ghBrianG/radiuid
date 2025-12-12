#!/usr/bin/env python3
"""
RadiUID Templates Package
Contains service files, completion scripts, and other templates
"""

import os
from typing import Optional

# Template directory path
TEMPLATES_DIR = os.path.dirname(__file__)


def get_template_path(filename: str) -> str:
    """Get the full path to a template file."""
    return os.path.join(TEMPLATES_DIR, filename)


def read_template(filename: str) -> str:
    """
    Read a template file and return its contents.

    Args:
        filename: Name of the template file

    Returns:
        Template file contents as string

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    path = get_template_path(filename)
    with open(path, 'r') as f:
        return f.read()


def read_template_safe(filename: str, default: Optional[str] = None) -> Optional[str]:
    """
    Read a template file, returning default if not found.

    Args:
        filename: Name of the template file
        default: Value to return if file not found

    Returns:
        Template file contents or default value
    """
    try:
        return read_template(filename)
    except FileNotFoundError:
        return default
