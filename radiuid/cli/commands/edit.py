#!/usr/bin/env python3
"""
Edit Commands
Handles 'edit' CLI commands for RadiUID
"""

import os
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..main import CLIRouter


def handle(cli: 'CLIRouter', arguments: str, _args_list: List[str]) -> None:
    """Handle edit commands"""

    # Edit help
    if arguments == "edit" or arguments == "edit ?":
        print("\n - edit config      |     Edit the RadiUID config file")
        print(" - edit clients     |     Edit RADIUS client config file for FreeRADIUS\n")
        return

    # Edit config
    if arguments == "edit config":
        _edit_config(cli, arguments)
        return

    # Edit clients
    if arguments == "edit clients":
        _edit_clients(cli, arguments)
        return


def _edit_config(cli: 'CLIRouter', arguments: str) -> None:
    """Edit RadiUID config file in vi"""
    cli._log_command(arguments)
    configfile = cli.context.config.config_file

    print(cli.ui.color("****************** You are about to edit the RadiUID config file in VI ******************", cli.ui.yellow))
    print(cli.ui.color("**************** It is recommend you use 'set' commands instead of this *****************", cli.ui.yellow))
    print(cli.ui.color("********************* Confirm that you know how to use the VI editor ********************", cli.ui.yellow))
    input("Hit CTRL-C to quit. Hit ENTER to continue\n>>>>>")

    os.system(f"vi {configfile}")


def _edit_clients(cli: 'CLIRouter', arguments: str) -> None:
    """Edit FreeRADIUS clients config file in vi"""
    cli._log_command(arguments)
    clientconfpath = cli.context.config.client_conf_path

    print(cli.ui.color("****************** You are about to edit the FreeRADIUS client file in VI ******************", cli.ui.yellow))
    print(cli.ui.color("***** It is recommend you use 'set client' and 'clear client' commands instead of this *****", cli.ui.yellow))
    print(cli.ui.color("*********************** Confirm that you know how to use the VI editor *********************", cli.ui.yellow))
    input("Hit CTRL-C to quit. Hit ENTER to continue\n>>>>>")

    os.system(f"vi {clientconfpath}")
