#!/usr/bin/env python3
"""
Clear Commands
Handles all 'clear' CLI commands for RadiUID
"""

import os
import time
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..main import CLIRouter


def handle(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Handle clear commands"""

    # Clear help
    if arguments == "clear" or arguments == "clear ?":
        _show_help()
        return

    # Individual clear helps
    if arguments in ("clear client", "clear client ?"):
        print("\n - clear client (<ip-block> | all) |  Examples: 'clear client 10.0.0.0/8'")
        print("                                   |            'clear client all'\n")
        return

    if arguments in ("clear munge", "clear munge ?"):
        print("\n - clear munge (<rule> | all) (<step> | all)  |  Examples: 'clear munge rule1'")
        print("                                              |            'clear munge rule10 step3'")
        print("                                              |            'clear munge all'\n")
        return

    if arguments in ("clear target", "clear target ?"):
        print("\n - clear target (<hostname>:<vsys-id> | all)  |  Examples: 'clear target 192.168.1.1:vsys1'")
        print("                                              |            'clear target pan1.domain.com:2'")
        print("                                              |            'clear target all'\n")
        return

    if arguments in ("clear mappings", "clear mappings ?"):
        print("\n - clear mappings (<hostname>:<vsys-id> | all) (<ip> | all)     |  Examples: 'clear mappings pan1.domain.com:vsys1 10.0.0.1'")
        print("                                                                |            'clear mappings 192.168.1.1:2 all'")
        print("                                                                |            'clear mappings all all'\n")
        return

    if arguments in ("clear livelog", "clear livelog ?"):
        print("\n - clear livelog tracker  |  Reset the live log tracker (re-read from beginning)\n")
        return

    # Clear livelog tracker
    if arguments == "clear livelog tracker":
        _clear_livelog_tracker(cli, arguments)
        return

    # Clear log
    if arguments == "clear log":
        _clear_log(cli)
        return

    # Clear acct-logs
    if arguments == "clear acct-logs":
        _clear_acct_logs(cli, arguments)
        return

    # Clear munge all
    if arguments == "clear munge all":
        _clear_munge_all(cli, arguments)
        return

    # Clear target all
    if arguments == "clear target all":
        _clear_target_all(cli, arguments)
        return

    # Clear commands with parameters
    if len(args_list) >= 3:
        cmd = cli.cat_list(args_list[:2])

        if cmd == "clear client":
            _clear_client(cli, arguments, args_list)
        elif cmd == "clear munge":
            _clear_munge(cli, arguments, args_list)
        elif cmd == "clear target":
            _clear_target(cli, arguments, args_list)
        elif cmd == "clear mappings":
            _clear_mappings(cli, arguments, args_list)


def _show_help() -> None:
    """Show help for clear commands"""
    print("\n - clear log                                                   |     Delete the content in the log file")
    print(" - clear acct-logs                                             |     Delete the log files currently in the FreeRADIUS accounting directory")
    print(" - clear livelog tracker                                       |     Reset the live log tracker (re-read from beginning)")
    print(" - clear client (<ip-block> | all)                             |     Delete one or all RADIUS client IP blocks in FreeRADIUS config file")
    print(" - clear munge (<rule> | all) (<step> | all)                   |     Delete one or all munge rules in the config file")
    print(" - clear target (<hostname>:<vsys-id> | all)                   |     Delete one or all firewall targets in the config file")
    print(" - clear mappings (<hostname>:<vsys-id> | all) (<ip> | all)    |     Remove one or all IP-to-User mappings from one or all firewalls\n")


def _clear_log(cli: 'CLIRouter') -> None:
    """Clear RadiUID log file"""
    logfile = cli.context.config.log_file
    print(cli.ui.color(f"********************* You are about to clear out the RadiUID log file... ({logfile}) ********************", cli.ui.yellow))
    input("Hit CTRL-C to quit. Hit ENTER to continue\n>>>>>")
    os.system(f"rm -f {logfile}")
    current_user = cli.service_controller.get_current_user()
    cli.file_manager.write_file(logfile, f"***********Logfile cleared via RadiUID command by {current_user}***********\n")
    print(cli.ui.color(f"********************* Cleared logfile: {logfile} ********************", cli.ui.yellow))


def _clear_acct_logs(cli: 'CLIRouter', arguments: str) -> None:
    """Clear FreeRADIUS accounting logs"""
    cli._log_command(arguments)
    radiuslogpath = cli.context.config.radius_log_path

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print("\n")

    filelist = cli.file_manager.list_files(radiuslogpath)
    if len(filelist) > 0:
        for file in filelist:
            print(file)
        print("\n\n")
        print(cli.ui.color(f"********************* You are about to delete all files, listed above, in directory... ({radiuslogpath}) ********************", cli.ui.yellow))
        input("Hit CTRL-C to quit. Hit ENTER to continue\n>>>>>")
        print("\n\n")
        cli.file_manager.remove_files(filelist)
        current_user = cli.service_controller.get_current_user()
        cli.file_manager.log_write("cli", f"##### FreeRADIUS accounting files deleted by user '{current_user}' #####")
        print("\n")
        cli.print_success()
    else:
        print(cli.ui.color(f"***** Directory {radiuslogpath} is currently empty *****", cli.ui.red))
        print(cli.ui.color("***** Nothing to do *****", cli.ui.red))

    print("\n")
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))


def _clear_client(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Clear FreeRADIUS client(s)"""
    cli._log_command(arguments)

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    if args_list[2] == "all":
        print("\n")
        cli.file_manager.log_write("cli", "**************** Removing all RADIUS client IP blocks ****************")
        clearresult = cli.file_manager.edit_freeradius_client("clear", [])
        if isinstance(clearresult, str) and "FATAL" in clearresult:
            print("\n")
            cli.file_manager.log_write("cli", cli.ui.color(clearresult, cli.ui.red))
            print("\n\n")
            cli.print_failure()
        else:
            print(cli.ui.make_table(["IP Block", "Family", "Shared Secret"], cli.file_manager.get_freeradius_clients()))
            print("\n")
            cli.print_success()
    else:
        existingclient = False
        currentclients = cli.file_manager.get_freeradius_clients()
        if isinstance(currentclients, str) and "FATAL" in currentclients:
            print("\n")
            cli.file_manager.log_write("cli", cli.ui.color(currentclients, cli.ui.red))
            print("\n\n")
            cli.print_failure()
        else:
            for client in currentclients:
                if client.get('IP Block') == args_list[2]:
                    existingclient = True
                    break

            if existingclient:
                print("\n")
                cli.file_manager.log_write("cli", f"**************** Removing client IP block {args_list[2]} ****************")
                cli.file_manager.edit_freeradius_client("clear", [{'IP Block': args_list[2]}])
                print(cli.ui.make_table(["IP Block", "Family", "Shared Secret"], cli.file_manager.get_freeradius_clients()))
                print("\n")
                cli.print_success()
            else:
                cli.file_manager.log_write("cli", cli.ui.color(f"**************** {args_list[2]} does not exist as a current client IP block ****************", cli.ui.yellow))
                cli.print_failure()

    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))


def _clear_munge_all(cli: 'CLIRouter', arguments: str) -> None:
    """Clear all munge rules"""
    cli._log_command(arguments)
    configfile = cli.context.config.config_file

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print("\n\n")
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   **************** Removing all munge configuration ****************\n")

    if cli.config_manager.get_config_item('munge') is None:
        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: No munge configuration currently exist in config****************\n", cli.ui.red))
    else:
        print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Deleting configuration items: ****************\n")
        cli.config_manager.show_config_item('xml', "none", 'munge')
        cli.config_manager.set_munge_config({})
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
        cli.config_manager.save()

    print("\n")
    cli.print_success()
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))


def _clear_munge(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Clear specific munge rule or step"""
    cli._log_command(arguments)
    configfile = cli.context.config.config_file

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    itemexists = False
    config_dict = cli.context.config_dict

    if len(args_list) >= 3:
        rulelist = []
        steplist = ['all']

        try:
            if config_dict and 'globalsettings' in config_dict:
                munge = config_dict['globalsettings'].get('munge', {})
                for rulename in munge.keys():
                    rulelist.append(rulename)
        except KeyError:
            print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: No munge configuration currently exist in config****************\n", cli.ui.red))

        if args_list[2] in rulelist:
            itemexists = True

        if itemexists:
            rule = args_list[2]
            if len(args_list) >= 4:
                munge = config_dict['globalsettings'].get('munge', {})
                for stepname in munge.get(rule, {}).keys():
                    if stepname != "match":
                        steplist.append(stepname)

                if args_list[3] in steplist:
                    itemexists = True
                else:
                    itemexists = False
                    print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: That step does not exist in {rule}****************\n", cli.ui.red))

                if itemexists:
                    step = args_list[3]
        else:
            print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: That rule does not exist****************\n", cli.ui.red))

        if itemexists:
            if len(args_list) > 3 and args_list[3] == "all":
                print("\n\n")
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Removing munge {rule}****************\n")
                cli.config_manager.set_munge_config({'clear': rule})
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
                cli.config_manager.save()
            elif len(args_list) > 3:
                print("\n\n")
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Removing munge {rule} {step}****************\n")
                cli.config_manager.set_munge_config({'clear': {rule: step}})
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
                cli.config_manager.save()
            else:
                itemexists = False
                print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Missing <step> or 'all' term after rule name****************\n", cli.ui.red))

            if itemexists:
                print("\n")
                cli.print_success()
        else:
            print("\n")
            cli.print_failure()

    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))


def _clear_target_all(cli: 'CLIRouter', arguments: str) -> None:
    """Clear all firewall targets"""
    cli._log_command(arguments)
    configfile = cli.context.config.config_file

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    if cli.config_manager.get_config_item('target') is None:
        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: No targets currently exist in config****************\n", cli.ui.red))
    else:
        print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Deleting configuration items: ****************\n")
        cli.config_manager.show_config_item('xml', "none", 'targets')
        cli.config_manager.clear_targets()
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
        cli.config_manager.save()

        if cli.config_manager.get_config_item('target') is None:
            cli.print_success()
        else:
            cli.print_failure()

    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))


def _clear_target(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Clear specific firewall target"""
    cli._log_command(arguments)
    configfile = cli.context.config.config_file

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    targetexists = False

    # Parse hostname and vsys
    if ":" in args_list[2]:
        hostname = args_list[2].split(":")[0]
        vsys = args_list[2].split(":")[1].replace("vsys", "")
    else:
        hostname = args_list[2]
        vsys = "1"

    try:
        targets = cli.context.targets or []
        for target in targets:
            if target.hostname == hostname and target.vsys == vsys:
                targetexists = True
                break

        if not targetexists:
            print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Target {hostname}:vsys{vsys} doesn't currently exist in config****************\n", cli.ui.red))
        else:
            print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Deleting target: {args_list[2]} ****************\n")
            targetremove = cli.config_manager.remove_target([{'hostname': hostname, "vsys": vsys}])
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
            cli.config_manager.save()

            if targetremove[0] == "pass":
                cli.print_success()
            else:
                cli.print_failure()
    except (NameError, AttributeError):
        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: No targets currently exist in config****************\n", cli.ui.red))

    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))


def _clear_mappings(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Clear IP-to-User mappings"""
    cli._log_command(arguments)

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))

    # Parse hostname and vsys
    if ":" in args_list[2]:
        hostname = args_list[2].split(":")[0]
        vsys = args_list[2].split(":")[1].replace("vsys", "")
    else:
        hostname = args_list[2]
        vsys = "1"

    keepgoing = True
    targets = list(cli.context.targets) if cli.context.targets else []

    # Check parameters
    if len(args_list[2:4]) != 2:
        cli.file_manager.log_write(
            "cli",
            cli.ui.color("********************* ERROR: Some parameters are missing. Use '", cli.ui.red) +
            cli.ui.color(f"{cli.runcmd} clear mappings ?", cli.ui.cyan) +
            cli.ui.color("' to see proper use and examples.********************", cli.ui.red)
        )
        keepgoing = False

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

    if keepgoing:
        if args_list[3].lower() != "all":
            if not cli.file_manager.validate_ip("address", args_list[3]):
                cli.file_manager.log_write("cli", cli.ui.color("****************FATAL: Bad IP Address****************", cli.ui.red))
                keepgoing = False

    if keepgoing:
        print("\n\n", cli.ui.color("********************* You are about to remove IP-to-User mappings. Please confirm... ********************", cli.ui.yellow))
        input("Hit CTRL-C to quit. Hit ENTER to continue\n>>>>>")
        cli.file_manager.scrub_targets("noisy", "scrub")
        print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Removing IP-to-User Mappings... ****************\n")

        if args_list[3].lower() == "all":
            cli.firewall.pull_api_key("quiet", targets)
            tempresult = cli.firewall.clear_uids(targets, "all")
        else:
            cli.firewall.pull_api_key("quiet", targets)
            tempresult = cli.firewall.clear_uids(targets, args_list[3])

        resultlist = []
        debug = ""
        for target_key in tempresult:
            tempdict = {"hostname": target_key}
            for command in tempresult[target_key]:
                if 'status="success"' in tempresult[target_key][command]:
                    tempdict[command] = cli.ui.color("success", cli.ui.green)
                else:
                    tempdict[command] = cli.ui.color("failed", cli.ui.red)
                    debug += tempresult[target_key][command] + "\n\n"
            resultlist.append(tempdict)

        print("\n")
        print(cli.ui.make_table(["hostname", "DP-CLEAR", "MP-CLEAR"], resultlist).replace("hostname", "HOSTNAME"))
        if debug:
            print("\n\n" + cli.ui.color(debug, cli.ui.red))
        print("\n")

    if keepgoing:
        cli.print_success()
    else:
        cli.print_failure()

    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))


def _clear_livelog_tracker(cli: 'CLIRouter', arguments: str) -> None:
    """Clear live log tracker file to re-read from beginning"""
    cli._log_command(arguments)

    header = f"########################## EXECUTING COMMAND: {arguments} ##########################"
    print(cli.ui.color(header, cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print("\n")

    tracker_file = cli.context.config.live_log_tracker

    if not tracker_file:
        print(cli.ui.color("ERROR: Live log tracker file is not configured.", cli.ui.red))
        print("Use 'set livelog tracker <path>' to configure it first.\n")
        cli.print_failure()
    elif not os.path.isfile(tracker_file):
        print(cli.ui.color(f"Tracker file does not exist: {tracker_file}", cli.ui.yellow))
        print("Nothing to clear - live log will be read from the beginning.\n")
        cli.print_success()
    else:
        # Show current position
        try:
            with open(tracker_file, 'r') as f:
                current_pos = f.read().strip() or "0"
            print(f"Current tracker position: {current_pos} bytes")
        except Exception:
            pass

        print(cli.ui.color(f"\nYou are about to reset the live log tracker: {tracker_file}", cli.ui.yellow))
        print("This will cause RadiUID to re-read the entire live log file from the beginning.\n")
        input("Hit CTRL-C to quit. Hit ENTER to continue\n>>>>>")

        try:
            os.remove(tracker_file)
            print(f"\nTracker file removed: {tracker_file}")
            print("Live log will be read from the beginning on next processing cycle.\n")
            cli.file_manager.log_write("cli", f"Live log tracker cleared: {tracker_file}")
            cli.print_success()
        except Exception as e:
            print(cli.ui.color(f"\nError removing tracker file: {e}", cli.ui.red))
            cli.print_failure()

    print(cli.ui.color("#" * len(header), cli.ui.magenta))
    print(cli.ui.color("#" * len(header), cli.ui.magenta))
