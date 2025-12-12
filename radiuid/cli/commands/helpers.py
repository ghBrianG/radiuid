#!/usr/bin/env python3
"""
CLI Command Helpers
Shared helper functions for CLI command output formatting.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import CLIRouter


def print_header(cli: 'CLIRouter', title: str) -> str:
    """
    Print command header and return it.

    Args:
        cli: CLIRouter instance
        title: Title text for the header

    Returns:
        The header string (for use with print_footer)
    """
    header = f"########################## {title} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    return header


def print_footer(cli: 'CLIRouter', header: str) -> None:
    """
    Print command footer.

    Args:
        cli: CLIRouter instance
        header: The header string returned from print_header
    """
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))


def print_service_block(cli: 'CLIRouter', title: str, output: str) -> None:
    """
    Print service control output block with header and footer.

    Args:
        cli: CLIRouter instance
        title: Title text for the header
        output: Service output to display
    """
    header = print_header(cli, title)
    print(output)
    print_footer(cli, header)
