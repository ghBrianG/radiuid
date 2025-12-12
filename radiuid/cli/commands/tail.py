#!/usr/bin/env python3
"""
Tail Commands
Handles 'tail' CLI commands for RadiUID
"""

import os
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..main import CLIRouter


def handle(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Handle tail commands"""

    # Tail help
    if arguments == "tail" or arguments == "tail ?":
        print("\n - tail log (<# of lines>)    |     Watch the RadiUID log file in real time\n")
        return

    # Tail log
    if cli.cat_list(args_list[:2]) == "tail log":
        _tail_log(cli, arguments, args_list)


def _tail_log(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Tail the RadiUID log file"""
    cli._log_command(arguments)
    logfile = cli.context.config.log_file

    header = f"########################## OUTPUT FROM FILE {logfile} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    if len(args_list) == 2:
        os.system(f"tail -fn 25 {logfile}")
    else:
        try:
            lineqty = int(args_list[2])
            os.system(f"tail -fn {lineqty} {logfile}")
        except ValueError:
            cli.file_manager.log_write(
                "cli",
                cli.ui.color(f"****************FATAL: '{args_list[2]}' is a bad input for number of lines. Please input a number****************", cli.ui.red)
            )

    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
