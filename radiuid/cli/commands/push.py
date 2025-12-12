#!/usr/bin/env python3
"""
Push Commands
Handles 'push' CLI commands for RadiUID
"""

from typing import TYPE_CHECKING, List
import re

if TYPE_CHECKING:
    from ..main import CLIRouter


def handle(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Handle push commands"""

    # Push help
    if arguments == "push" or arguments == "push ?":
        print("\n - push (<hostname>:<vsys-id> | all) [parameters]  |  Parameters: (<username>, <ip address>, bypass-munge)")
        print("                                                   |              ")
        print("                                                   |  Examples:   'push 192.168.1.1:vsys1 administrator 10.0.0.1 bypass-munge'")
        print("                                                   |              'push pan1.domain.com:3 jsmith 172.30.50.100'")
        print("                                                   |              'push all jsmith 172.30.50.100'\n")
        return

    # Push with parameters
    if len(args_list) >= 2:
        _push_mapping(cli, arguments, args_list)


def _push_mapping(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Push a User-ID mapping to firewall(s)"""
    cli._log_command(arguments)

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    keepgoing = True
    pushuser = True
    targets = list(cli.context.targets) if cli.context.targets else []

    # Check for bypass-munge flag
    tomunge = True
    if len(args_list) > 4:
        if args_list[4] == 'bypass-munge':
            tomunge = False
            cli.context.to_munge = False

    # Parse hostname and vsys
    if ":" in args_list[1]:
        hostname = args_list[1].split(":")[0]
        vsys = args_list[1].split(":")[1].replace("vsys", "")
    else:
        hostname = args_list[1]
        vsys = "1"

    # Check for missing parameters
    if len(args_list[2:4]) != 2:
        cli.file_manager.log_write(
            "cli",
            cli.ui.color("********************* ERROR: Some parameters are missing. Use '", cli.ui.red) +
            cli.ui.color(f"{cli.runcmd} push ?", cli.ui.cyan) +
            cli.ui.color("' to see proper use and examples.********************", cli.ui.red)
        )
        pushuser = False
        keepgoing = False

    # Check target hostname against config
    if keepgoing:
        if hostname.lower() != "all":
            keepgoing = False
            for target in targets:
                if target.hostname == hostname and target.vsys == vsys:
                    keepgoing = True
                    targets = [target]
                    break

            if not keepgoing:
                cli.file_manager.log_write(
                    "cli",
                    cli.ui.color("********************* ERROR: Target ", cli.ui.red) +
                    cli.ui.color(f"{hostname}:vsys{vsys}", cli.ui.cyan) +
                    cli.ui.color(" does not exist in config. Please configure it.********************", cli.ui.red)
                )
                pushuser = False

    # Validate IP address
    if keepgoing:
        if not cli.file_manager.validate_ip("address", args_list[3]):
            cli.file_manager.log_write("cli", cli.ui.color("****************FATAL: Bad IP Address****************", cli.ui.red))
            pushuser = False
        else:
            # Scrub targets and push the mapping
            cli.file_manager.scrub_targets("noisy", "scrub")
            cli.firewall.pull_api_key("noisy", targets)
            cli.firewall.push_uids(
                {args_list[3]: {"username": args_list[2], "status": "start"}},
                []
            )

    if pushuser:
        cli.print_success()
    else:
        cli.print_failure()

    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
