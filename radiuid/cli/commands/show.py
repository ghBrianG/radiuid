#!/usr/bin/env python3
"""
Show Commands
Handles all 'show' CLI commands for RadiUID
"""

import os
import re
from typing import TYPE_CHECKING, List
from xml.etree import ElementTree

from .helpers import print_header, print_footer

if TYPE_CHECKING:
    from ..main import CLIRouter


def handle(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Handle show commands"""

    # Show help
    if arguments == "show" or arguments == "show ?":
        _show_help(cli)
        return

    # Show config help
    if arguments == "show config ?":
        _show_config_help(cli)
        return

    # Show run help
    if arguments == "show run ?":
        _show_run_help(cli)
        return

    # Show mappings help
    if arguments == "show mappings" or arguments == "show mappings ?":
        _show_mappings_help(cli)
        return

    # Show log
    if arguments == "show log":
        _show_log(cli, arguments)
        return

    # Show acct-logs
    if arguments == "show acct-logs":
        _show_acct_logs(cli, arguments)
        return

    # Show config/run as set commands
    if arguments == "show run set" or arguments == "show config set":
        _show_config_set(cli, arguments)
        return

    # Show config/run as XML
    if arguments in ("show run", "show run xml", "show config", "show config xml"):
        _show_config_xml(cli, arguments)
        return

    # Show clients table
    if arguments == "show clients" or arguments == "show clients table":
        _show_clients_table(cli, arguments)
        return

    # Show clients file
    if arguments == "show clients file":
        _show_clients_file(cli, arguments)
        return

    # Show status
    if arguments == "show status":
        _show_status(cli, arguments)
        return

    # Show livelog settings
    if arguments == "show livelog":
        _show_livelog(cli, arguments)
        return

    # Show mappings with target
    if cli.cat_list(args_list[:2]) == "show mappings" and len(args_list) > 2:
        if re.findall(r"^[0-9A-Za-z]", args_list[2]):
            _show_mappings(cli, arguments, args_list)
            return


def _show_help(_cli: 'CLIRouter') -> None:
    """Show help for show commands"""
    print("\n - show log                                                  |     Show the RadiUID log file")
    print(" - show acct-logs                                            |     Show the log files currently in the FreeRADIUS accounting directory")
    print(" - show livelog                                              |     Show the live log file settings (file, tracker, enabled)")
    print(" - show run (xml | set)                                      |     Show the RadiUID configuration in XML format (default) or as set commands")
    print(" - show config (xml | set)                                   |     Show the RadiUID configuration in XML format (default) or as set commands")
    print(" - show clients (file | table)                               |     Show the FreeRADIUS client config file")
    print(" - show status                                               |     Show the RadiUID and FreeRADIUS service statuses")
    print(" - show mappings (<hostname>:<vsys-id> | all | consistency)  |     Show the current IP-to-User mappings of one or all targets or check consistency\n")


def _show_config_help(_cli: 'CLIRouter') -> None:
    """Show help for show config command"""
    print("\n - show config (xml | set)  |   Show the RadiUID configuration in XML format (default) or as set commands")
    print("                            |  ")
    print("                            |   Examples: 'show config'")
    print("                            |             'show config xml'")
    print("                            |             'show config set'\n")


def _show_run_help(_cli: 'CLIRouter') -> None:
    """Show help for show run command"""
    print("\n - show run (xml | set)  |   Show the RadiUID configuration in XML format (default) or as set commands")
    print("                         |  ")
    print("                         |   Examples: 'show run'")
    print("                         |             'show run xml'")
    print("                         |             'show run set'\n")


def _show_mappings_help(_cli: 'CLIRouter') -> None:
    """Show help for show mappings command"""
    print("\n - show mappings (<hostname>:<vsys-id> | all | consistency)  |   Show the current IP-to-User mappings of one or all targets or")
    print("                                                             |    check the consistency of IP-to-User mappings in all targets")
    print("                                                             |  ")
    print("                                                             |   Examples: 'show mappings 192.168.1.1:vsys1'")
    print("                                                             |             'show mappings pan1.domain.com'")
    print("                                                             |             'show mappings pan1.domain.com:4'")
    print("                                                             |             'show mappings all'")
    print("                                                             |             'show mappings consistency'\n")


def _show_log(cli: 'CLIRouter', arguments: str) -> None:
    """Show RadiUID log file"""
    cli._log_command(arguments)
    logfile = cli.context.config.log_file
    header = print_header(cli, f"OUTPUT FROM FILE {logfile}")
    os.system(f"more {logfile}")
    print_footer(cli, header)


def _show_acct_logs(cli: 'CLIRouter', arguments: str) -> None:
    """Show FreeRADIUS accounting log files"""
    cli._log_command(arguments)
    radiuslogpath = cli.context.config.radius_log_path
    header = print_header(cli, f"FILES IN DIRECTORY {radiuslogpath}")
    print("\n")
    filelist = cli.file_manager.list_files(radiuslogpath)
    if len(filelist) > 0:
        for file in filelist:
            print(file)
    else:
        print(cli.ui.color(f"***** Directory {radiuslogpath} is currently empty *****", cli.ui.red))
    print("\n")
    print_footer(cli, header)


def _show_config_set(cli: 'CLIRouter', arguments: str) -> None:
    """Show configuration as set commands"""
    cli._log_command(arguments)
    print(cli.ui.color("NOTE:", cli.ui.cyan) + f"  Use command '{cli.ui.color(cli.runcmd + ' show config xml', cli.ui.green)}' to see configuration in XML format\n")
    configfile = cli.context.config.config_file
    header = print_header(cli, f"OUTPUT FROM FILE {configfile}")
    print(cli.config_manager.show_config_item('set', "auto", 'config'))
    print_footer(cli, header)


def _show_config_xml(cli: 'CLIRouter', arguments: str) -> None:
    """Show configuration as XML"""
    cli._log_command(arguments)
    print(cli.ui.color("NOTE:", cli.ui.cyan) + f"  Use command '{cli.ui.color(cli.runcmd + ' show config set', cli.ui.green)}' to see configuration in form of CLI commands\n")
    configfile = cli.context.config.config_file
    header = print_header(cli, f"OUTPUT FROM FILE {configfile}")
    print("\n")
    print("###############################################################")
    print("################### Main RadiUID XML Config ###################")
    print("###############################################################")
    cli.config_manager.show_config_item('xml', "none", 'config')
    print("###############################################################")
    print("###############################################################")
    print("\n\n")

    clientconfig = cli.file_manager.get_freeradius_clients_raw()
    if not isinstance(clientconfig, str) or "FATAL" not in clientconfig:
        print("###############################################################")
        print("################### FreeRADIUS Client Config ##################")
        print("###############################################################")
        print(clientconfig if clientconfig else "")
        print("###############################################################")
        print("###############################################################")
        print("\n")
    else:
        print(cli.ui.color("********** FreeRADIUS config file doesn't exist **********", cli.ui.yellow))
        print("\n")

    print_footer(cli, header)


def _show_clients_table(cli: 'CLIRouter', arguments: str) -> None:
    """Show FreeRADIUS clients as table"""
    cli._log_command(arguments)
    header = print_header(cli, "CURRENT FREERADIUS RADIUS CLIENTS")
    print("\n")

    clientinfo = cli.file_manager.get_freeradius_clients()
    if isinstance(clientinfo, str) and "FATAL" in clientinfo:
        cli.file_manager.log_write("cli", cli.ui.color(clientinfo, cli.ui.red))
        print("\n\n")
        cli.print_failure()
    else:
        print(cli.ui.make_table(["IP Block", "Family", "Shared Secret"], clientinfo))
        print("\n\n")
        cli.print_success()

    print_footer(cli, header)


def _show_clients_file(cli: 'CLIRouter', arguments: str) -> None:
    """Show FreeRADIUS clients config file"""
    cli._log_command(arguments)
    clientconfpath = cli.context.config.client_conf_path
    header = print_header(cli, f"OUTPUT FROM FILE {clientconfpath}")
    os.system(f"more {clientconfpath}")
    print_footer(cli, header)


def _show_status(cli: 'CLIRouter', arguments: str) -> None:
    """Show RadiUID and FreeRADIUS service statuses"""
    cli._log_command(arguments)

    radservicename = cli.context.system_info.radius_service_name if cli.context.system_info else "radiusd"

    radiuid_status = cli.service_controller.control_service("status", "radiuid")
    freeradius_status = cli.service_controller.control_service("status", radservicename)

    # RadiUID check
    header = print_header(cli, "CHECKING RADIUID")
    print(radiuid_status.get("action", ""))
    print_footer(cli, header)

    status = radiuid_status.get("status", "")
    if status == "not-found":
        print(cli.ui.color("\n\n********** RADIUID IS NOT INSTALLED YET **********\n\n", cli.ui.yellow))
    elif status == "running":
        print(cli.ui.color("\n\n********** RADIUID IS CURRENTLY RUNNING **********\n\n", cli.ui.green))
    elif status == "dead":
        print(cli.ui.color("\n\n********** RADIUID IS CURRENTLY NOT RUNNING **********\n\n", cli.ui.yellow))

    # FreeRADIUS check
    header = print_header(cli, "CHECKING FREERADIUS")
    print(freeradius_status.get("action", ""))
    print_footer(cli, header)

    status = freeradius_status.get("status", "")
    if status == "not-found":
        print(cli.ui.color("\n\n********** FREERADIUS IS NOT INSTALLED YET **********\n\n", cli.ui.yellow))
    elif status == "running":
        print(cli.ui.color("\n\n********** FREERADIUS IS CURRENTLY RUNNING **********\n\n", cli.ui.green))
    elif status == "dead":
        print(cli.ui.color("\n\n********** FREERADIUS IS CURRENTLY NOT RUNNING **********\n\n", cli.ui.yellow))


def _show_mappings(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Show IP-to-User mappings for targets"""
    cli._log_command(arguments)

    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    # Parse hostname and vsys
    if ":" in args_list[2]:
        hostname = args_list[2].split(":")[0]
        vsys = args_list[2].split(":")[1].replace("vsys", "")
    else:
        hostname = args_list[2]
        vsys = "1"

    keepgoing = True
    pulluids = True
    targets = list(cli.context.targets) if cli.context.targets else []

    # Check target hostname against config
    if hostname.lower() != "all" and hostname.lower() != "consistency":
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
                cli.ui.color(args_list[2], cli.ui.cyan) +
                cli.ui.color(" does not exist in the config. Please configure it.********************", cli.ui.red)
            )
            pulluids = False

    # Pull and display mappings
    if keepgoing:
        cli.file_manager.scrub_targets("noisy", "scrub")
        cli.firewall.pull_api_key("quiet", targets)
        uidxmldict = cli.firewall.pull_uids(targets)

        print("\n\n")

        if hostname.lower() == "consistency":
            print(cli.data_processor.map_consistency_check(uidxmldict))
            print("\n\n")
        else:
            for uidset in uidxmldict:
                currentuidset = ElementTree.fromstring(uidxmldict[uidset])
                print(f"************{uidset}************")

                result_dict = cli.config_manager.tinyxmltodict(currentuidset)
                response = result_dict.get('response', {})
                result = response.get('result', {})

                if not isinstance(result, dict) or "<count>0</count>" in uidxmldict[uidset]:
                    print("\n" + cli.ui.color("************No current mappings************", cli.ui.yellow))
                else:
                    entries = result.get('entry', [])
                    if isinstance(entries, dict):
                        entries = [entries]
                    print(cli.ui.make_table(["ip", "user", 'type', 'idle_timeout', 'timeout', 'vsys'], entries))
                print("\n\n")

    if pulluids:
        cli.print_success()
    else:
        cli.print_failure()

    print_footer(cli, header)


def _show_livelog(cli: 'CLIRouter', arguments: str) -> None:
    """Show live log file settings"""
    cli._log_command(arguments)

    header = print_header(cli, "LIVE LOG SETTINGS")
    print("\n")

    config = cli.context.config

    # Get live log settings
    live_log_file = config.live_log_file or "(not set)"
    live_log_tracker = config.live_log_tracker or "(not set)"
    live_log_enabled = config.live_log_enabled

    # Get tracker position if file exists
    tracker_position = "N/A"
    if config.live_log_tracker and os.path.isfile(config.live_log_tracker):
        try:
            with open(config.live_log_tracker, 'r') as f:
                tracker_position = f.read().strip() or "0"
        except Exception:
            tracker_position = "(error reading)"

    # Get live log file size if file exists
    live_log_size = "N/A"
    if config.live_log_file and os.path.isfile(config.live_log_file):
        try:
            live_log_size = str(os.path.getsize(config.live_log_file))
        except Exception:
            live_log_size = "(error reading)"

    # Display settings
    enabled_color = cli.ui.green if live_log_enabled else cli.ui.yellow
    enabled_text = "true" if live_log_enabled else "false"

    print(f"  Live Log File:      {live_log_file}")
    print(f"  Live Log Size:      {live_log_size} bytes")
    print(f"  Tracker File:       {live_log_tracker}")
    print(f"  Tracker Position:   {tracker_position} bytes")
    print(f"  Enabled:            {cli.ui.color(enabled_text, enabled_color)}")
    print("\n")

    print_footer(cli, header)
