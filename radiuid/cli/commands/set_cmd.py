#!/usr/bin/env python3
"""
Set Commands
Handles all 'set' CLI commands for RadiUID
"""

import os
import re
import time
from typing import TYPE_CHECKING, List

from .helpers import print_header, print_footer

if TYPE_CHECKING:
    from ..main import CLIRouter


def handle(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Handle set commands"""

    # Set help
    if arguments == "set" or arguments == "set ?":
        _show_help(cli)
        return

    # Individual setting helps
    if arguments in ("set logfile", "set logfile ?"):
        print("\n - set logfile <file path>  |  Example: 'set logfile /etc/radiuid/radiuid.log'\n")
        return

    if arguments in ("set radiuslogpath", "set radiuslogpath ?"):
        print("\n - set radiuslogpath <directory path>  |  Example: 'set radiuslogpath /var/log/radius/radacct/'\n")
        return

    if arguments in ("set acctlogcopypath", "set acctlogcopypath ?"):
        print("\n - set acctlogcopypath <directory path>  |  Example: 'set acctlogcopypath /root/logs/acctlogs/'\n")
        return

    if arguments in ("set xmloutputpath", "set xmloutputpath ?"):
        print("\n - set xmloutputpath <directory path>  |  Example: 'set xmloutputpath /var/log/radiuid/xml/'\n")
        return

    if arguments in ("set maxloglines", "set maxloglines ?"):
        print("\n - set maxloglines <number-of-lines>  |  Examples: 'set maxloglines 1000'   (circular logging enabled at 1000 lines)")
        print("                                      |            'set maxloglines 0'      (circular logging disabled)")
        return

    if arguments in ("set userdomain", "set userdomain ?"):
        print("\n - set userdomain (none | <domain name>)  |  Examples: 'set userdomain domain.com'")
        print("                                          |            'set userdomain none'\n")
        return

    if arguments in ("set timeout", "set timeout ?"):
        print("\n - set timeout <minutes>  |  Example: 'set timeout 60'\n")
        return

    if arguments in ("set looptime", "set looptime ?"):
        print("\n - set looptime <seconds>  |  Example: 'set looptime 10'\n")
        return

    if arguments in ("set tlsversion", "set tlsversion ?"):
        print("\n - set tlsversion (1.0 | 1.1 | 1.2)  |  Example: 'set tlsversion 1.2'\n")
        return

    if arguments in ("set radiusstopaction", "set radiusstopaction ?"):
        print("\n - set radiusstopaction (clear | ignore | push)  |  Example: 'set radiusstopaction clear'\n")
        return

    if arguments in ("set client", "set client ?"):
        print("\n - set client (ipv4|ipv6) <ip-block> <secret>  |  Example: 'set client ipv4 10.0.0.0/8 password123'\n")
        return

    if arguments in ("set target", "set target ?"):
        _show_target_help()
        return

    if arguments in ("set munge", "set munge ?"):
        _show_munge_help()
        return

    if arguments in ("set livelog", "set livelog ?"):
        _show_livelog_help()
        return

    # Actual set commands
    if len(args_list) >= 3:
        cmd = cli.cat_list(args_list[:2])

        if cmd == "set logfile":
            _set_logfile(cli, arguments, args_list)
        elif cmd == "set maxloglines":
            _set_maxloglines(cli, arguments, args_list)
        elif cmd == "set radiuslogpath":
            _set_radiuslogpath(cli, arguments, args_list)
        elif cmd == "set acctlogcopypath":
            _set_acctlogcopypath(cli, arguments, args_list)
        elif cmd == "set xmloutputpath":
            _set_xmloutputpath(cli, arguments, args_list)
        elif cmd == "set userdomain":
            _set_userdomain(cli, arguments, args_list)
        elif cmd == "set timeout":
            _set_timeout(cli, arguments, args_list)
        elif cmd == "set looptime":
            _set_looptime(cli, arguments, args_list)
        elif cmd == "set tlsversion":
            _set_tlsversion(cli, arguments, args_list)
        elif cmd == "set radiusstopaction":
            _set_radiusstopaction(cli, arguments, args_list)
        elif cmd == "set client":
            _set_client(cli, arguments, args_list)
        elif cmd == "set target":
            _set_target(cli, arguments, args_list)
        elif cmd == "set munge":
            _set_munge(cli, arguments, args_list)
        elif cmd == "set livelog":
            _set_livelog(cli, arguments, args_list)


def _show_help(_cli: 'CLIRouter') -> None:
    """Show help for set commands"""
    print("\n - set logfile <file path>                       |     Set the RadiUID logfile path")
    print(" - set radiuslogpath <directory path>            |     Set the path used to find FreeRADIUS accounting log files")
    print(" - set acctlogcopypath <directory path>          |     Set the path where RadiUID should copy acct log files before deletion")
    print(" - set xmloutputpath <directory path>            |     Set the path where RadiUID should save generated XML files")
    print(" - set maxloglines <number-of-lines>             |     Set the max number of lines allowed in the log ('0' turns circular logging off)")
    print(" - set userdomain (none | <domain name>)         |     Set the domain name prepended to User-ID mappings")
    print(" - set timeout <minutes>                         |     Set the timeout (in minutes) for User-ID mappings sent to the firewall targets")
    print(" - set looptime <seconds>                        |     Set the waiting loop time (in seconds) to pause between checks of the RADIUS logs")
    print(" - set tlsversion (1.0 | 1.1 | 1.2)              |     Set the version of TLS used for XML API communication with the firewall targets")
    print(" - set radiusstopaction (clear | ignore | push)  |     Set the action taken by RadiUID when RADIUS stop messages are received")
    print(" - set client (ipv4|ipv6) <ip-block> <secret>    |     Set configuration elements for RADIUS clients to send accounting data FreeRADIUS")
    print(" - set munge <rule>.<step> [parameters]          |     Set munge (string processing rules) for User-IDs")
    print(" - set target <hostname>:<vsys-id> [parameters]  |     Set configuration elements for existing or new firewall targets")
    print(" - set livelog <option> <value>                  |     Configure live log file processing (for NPS logs)\n")


def _show_target_help() -> None:
    """Show help for set target command"""
    print("\n - set target <hostname>:<vsys-id> [parameters]  |  Parameters: hostname and vsys <hostname>:<vsys-id>")
    print("                                                 |              username <username> ")
    print("                                                 |              password <password> ")
    print("                                                 |              port  <TCP port number>")
    print("                                                 |              ")
    print("                                                 |  Examples:   'set target 192.168.1.1 username admin'")
    print("                                                 |              'set target pan1.domain.com:vsys1 password P@s$w0rd'")
    print("                                                 |              'set target 10.0.0.10:2 username admin password P@ssword")
    print("                                                 |              'set target 10.0.0.10:2 username admin password P@ssword port 4433\n")


def _show_munge_help() -> None:
    """Show help for set munge command"""
    print("\n - set munge <rule>.<step> [parameters] |  Parameters: match (any | <regex>) (complete | partial)")
    print("                                        |              set-variable <variable name> (from-match | from-string) <regex or string>")
    print("                                        |              assemble <variable name> <variable name> ... ")
    print("                                        |              accept")
    print("                                        |              discard")
    print("                                        |              ")
    print("                                        |  Examples:   The below rule-set would allow through any user with the domain \"safedomain.com\" in their User-ID,")
    print("                                        |              then it would append the domain \"dangerous.com\" to any others")
    print("                                        |")
    print("                                        |              set munge 1.0 match \".*safedomain.com.*\" complete")
    print("                                        |              set munge 1.1 accept")
    print("                                        |              set munge 2.0 match any")
    print("                                        |              set munge 2.1 set-variable user from-match \".*\"")
    print("                                        |              set munge 2.2 set-variable dngr from-string \"dangerous.com\"")
    print("                                        |              set munge 2.3 set-variable slsh from-string \"\\\\\"")
    print("                                        |              set munge 2.4 assemble dngr slsh user")


def _prompt_network_mount(cli: 'CLIRouter', path: str) -> None:
    """Prompt user if the path is on a network mount and configure service dependency"""
    from ...installer.system_setup import SystemInstaller

    print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   Is this path on a network share/mount?", cli.ui.cyan))
    answer = cli.ui.yesorno("Configure RadiUID service to wait for mount before starting?")

    if answer == 'yes':
        # Extract the mount point from the path (usually the first or second directory).
        # e.g., /mnt/accountinglogs/server1/ -> /mnt/accountinglogs
        path_parts = path.strip('/').split('/')
        if len(path_parts) >= 2:
            default_mount = '/' + '/'.join(path_parts[:2])
        else:
            default_mount = '/' + path_parts[0] if path_parts else path

        mount_point = input(cli.ui.color(f"===== Enter mount point path [{default_mount}]: ", cli.ui.cyan)).strip()
        if not mount_point:
            mount_point = default_mount

        # Validate the mount path
        if not mount_point.startswith('/'):
            print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Mount path must be an absolute path starting with /****************", cli.ui.red))
            return

        # Convert to systemd mount unit name for display.
        mount_unit = mount_point.strip('/').replace('/', '-') + '.mount'

        print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Configuring service to wait for mount: {mount_point}****************", cli.ui.yellow))
        print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Systemd mount unit: {mount_unit}****************\n", cli.ui.cyan))

        installer = SystemInstaller(ui=cli.ui)
        installer.install_service(mount_point=mount_point)

        print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Mount dependency configured. Run 'service radiuid restart' to apply.****************\n", cli.ui.green))


def _set_logfile(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set the logfile path"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2]
    configfile = cli.context.config.config_file

    if cli.config_manager.get_config_item('logfile') == value:
        print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Entered value is the same as current value****************\n", cli.ui.green))
    else:
        pathcheck = cli.file_manager.validate_path("file", value)
        if pathcheck["status"] == "fail":
            for error in pathcheck.get("errors", []):
                print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: {error}****************", cli.ui.red))
        elif pathcheck["status"] == "pass":
            newlogfiledir = cli.file_manager.strip_filepath(value)[0]
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Making sure directory: {newlogfiledir} exists...creating if not****************\n")
            os.system(f'mkdir -p {newlogfiledir}')
            try:
                current_user = cli.service_controller.get_current_user()
                cli.file_manager.write_file(value, f"***********Logfile created via RadiUID command by {current_user}***********\n")
                cli.config_manager.set_config_item('logfile', value)
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
                cli.config_manager.save()
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <logfile> configuration element changed to :\n")
                cli.config_manager.show_config_item('xml', "none", 'logfile')
            except IOError:
                print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: One of the directory names already exists as a file or vice-versa****************\n", cli.ui.red))

        if cli.config_manager.get_config_item('logfile') == value:
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_maxloglines(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set max log lines"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2]
    configfile = cli.context.config.config_file

    if cli.config_manager.get_config_item('maxloglines') == value:
        print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Entered value is the same as current value****************\n", cli.ui.green))
    else:
        try:
            int(value)
            keepgoing = True
        except ValueError:
            print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Entered value must be a number****************\n", cli.ui.red))
            keepgoing = False

        if keepgoing:
            cli.config_manager.set_config_item('maxloglines', value)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
            cli.config_manager.save()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <maxloglines> configuration element changed to :\n")
            cli.config_manager.show_config_item('xml', "none", 'maxloglines')

        if cli.config_manager.get_config_item('maxloglines') == value:
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_radiuslogpath(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set RADIUS log path"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2]
    configfile = cli.context.config.config_file

    if cli.config_manager.get_config_item('radiuslogpath') == value:
        print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Entered value is the same as current value****************\n", cli.ui.green))
    else:
        pathcheck = cli.file_manager.validate_path("dir", value)
        if pathcheck["status"] == "fail":
            for error in pathcheck.get("errors", []):
                print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: {error}****************", cli.ui.red))
        elif pathcheck["status"] == "pass":
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Making sure directory: {value} exists****************\n")
            pathexists = cli.file_manager.file_exists(value)
            if pathexists == "no":
                print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************WARNING: Directory path doesn't exist. You may need to install FreeRADIUS****************\n", cli.ui.yellow))
            cli.config_manager.set_config_item('radiuslogpath', value)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
            cli.config_manager.save()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <radiuslogpath> configuration element changed to :\n")
            cli.config_manager.show_config_item('xml', "none", 'radiuslogpath')

            # Check if this is a network mount path
            _prompt_network_mount(cli, value)

        if cli.config_manager.get_config_item('radiuslogpath') == value:
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_acctlogcopypath(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set accounting log copy path"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2]
    configfile = cli.context.config.config_file

    if cli.config_manager.get_config_item('acctlogcopypath') == value:
        print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Entered value is the same as current value****************\n", cli.ui.green))
    else:
        if value.lower() != "none":
            pathcheck = cli.file_manager.validate_path("dir", value)
        else:
            pathcheck = {"status": "pass", "errors": []}

        if pathcheck["status"] == "fail":
            for error in pathcheck.get("errors", []):
                print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: {error}****************", cli.ui.red))
        elif pathcheck["status"] == "pass":
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Making sure directory: {value} exists****************\n")
            if value.lower() != "none":
                pathexists = cli.file_manager.file_exists(value)
                if pathexists == "no":
                    print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************WARNING: Directory path doesn't exist****************\n", cli.ui.yellow))

            config_value = None if value.lower() == "none" else value
            cli.config_manager.set_config_item('acctlogcopypath', config_value)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
            cli.config_manager.save()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <acctlogcopypath> configuration element changed to :\n")
            cli.config_manager.show_config_item('xml', "none", 'acctlogcopypath')

        if cli.config_manager.get_config_item('acctlogcopypath') == value:
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_xmloutputpath(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set the XML output path"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2]
    configfile = cli.context.config.config_file

    if cli.config_manager.get_config_item('xmloutputpath') == value:
        print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Entered value is the same as current value****************\n", cli.ui.green))
    else:
        if value.lower() != "none":
            pathcheck = cli.file_manager.validate_path("dir", value)
        else:
            pathcheck = {"status": "pass", "errors": []}

        if pathcheck["status"] == "fail":
            for error in pathcheck.get("errors", []):
                print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: {error}****************", cli.ui.red))
        elif pathcheck["status"] == "pass":
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Making sure directory: {value} exists****************\n")
            if value.lower() != "none":
                pathexists = cli.file_manager.file_exists(value)
                if pathexists == "no":
                    print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************WARNING: Directory path doesn't exist****************\n", cli.ui.yellow))

            config_value = None if value.lower() == "none" else value
            cli.config_manager.set_config_item('xmloutputpath', config_value)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
            cli.config_manager.save()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <xmloutputpath> configuration element changed to :\n")
            cli.config_manager.show_config_item('xml', "none", 'xmloutputpath')

        if cli.config_manager.get_config_item('xmloutputpath') == value:
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_userdomain(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set user domain"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    entereduserdomain = args_list[2]
    configfile = cli.context.config.config_file

    if cli.config_manager.get_config_item('userdomain') == entereduserdomain:
        print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Entered value is the same as current value****************\n", cli.ui.green))
    else:
        domaincheck = cli.file_manager.validate_domain_name(entereduserdomain)
        if domaincheck["status"] == "fail":
            for message in domaincheck["messages"]:
                # Messages are strings, not dicts
                print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: {message}****************\n", cli.ui.red))
        elif domaincheck["status"] == "pass":
            if entereduserdomain != "none":
                for message in domaincheck["messages"]:
                    # Messages are strings - check if it's a warning
                    if "warning" in message.lower():
                        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{message}****************\n", cli.ui.yellow))
            else:
                entereduserdomain = None

            cli.config_manager.set_config_item('userdomain', entereduserdomain)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
            cli.config_manager.save()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <userdomain> configuration element changed to :\n")
            cli.config_manager.show_config_item('xml', "none", 'userdomain')

        if str(cli.config_manager.get_config_item('userdomain')) == str(entereduserdomain):
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_timeout(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set timeout"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2]
    configfile = cli.context.config.config_file
    maxtimeout = 1440  # 24 hours

    try:
        timeoutval = int(value)
        if timeoutval == 0:
            print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Timeout value must be a number between 1 and 1440****************\n", cli.ui.red))
        elif int(cli.config_manager.get_config_item('timeout') or 0) == timeoutval:
            print(cli.ui.color(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Entered value is the same as current value****************\n", cli.ui.green))
        elif timeoutval > maxtimeout:
            print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Timeout cannot exceed 1440 minutes (24 hours)****************\n", cli.ui.red))
        else:
            cli.config_manager.set_config_item('timeout', value)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
            cli.config_manager.save()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <timeout> configuration element changed to :\n")
            cli.config_manager.show_config_item('xml', "none", 'timeout')

            if cli.config_manager.get_config_item('timeout') == value:
                cli.print_success()
            else:
                cli.print_failure()
    except ValueError:
        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Timeout value must be a number between 1 and 1440****************\n", cli.ui.red))

    print_footer(cli, header)


def _set_looptime(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set loop time"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2]
    configfile = cli.context.config.config_file

    try:
        int(value)
        inputgood = True
    except ValueError:
        inputgood = False
        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Looptime value must be an integer****************\n", cli.ui.red))

    if inputgood:
        cli.config_manager.extend_config_schema()
        cli.config_manager.set_config_item('looptime', value)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
        cli.config_manager.save()
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <looptime> configuration element changed to :\n")
        cli.config_manager.show_config_item('xml', "none", 'looptime')

        if cli.config_manager.get_config_item('looptime') == value:
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_tlsversion(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set TLS version"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2].lower()
    configfile = cli.context.config.config_file

    if value not in ("1.0", "1.1", "1.2"):
        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Acceptable versions are '1.0', '1.1', and '1.2'****************\n", cli.ui.red))
    else:
        cli.config_manager.extend_config_schema()
        cli.config_manager.set_config_item('tlsversion', value)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
        cli.config_manager.save()
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <tlsversion> configuration element changed to :\n")
        cli.config_manager.show_config_item('xml', "none", 'tlsversion')

        if cli.config_manager.get_config_item('tlsversion') == value:
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_radiusstopaction(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set RADIUS stop action"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    value = args_list[2].lower()
    configfile = cli.context.config.config_file

    if value not in ("clear", "ignore", "push"):
        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: Acceptable actions are 'clear', 'ignore', and 'push'****************\n", cli.ui.red))
    else:
        cli.config_manager.extend_config_schema()
        cli.config_manager.set_config_item('radiusstopaction', value)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
        cli.config_manager.save()
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   <radiusstopaction> configuration element changed to :\n")
        cli.config_manager.show_config_item('xml', "none", 'radiusstopaction')

        if cli.config_manager.get_config_item('radiusstopaction') == value:
            cli.print_success()
        else:
            cli.print_failure()

    print_footer(cli, header)


def _set_client(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set FreeRADIUS client"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    family = args_list[2]

    if family in ("ipv4", "ipv6"):
        if len(args_list) > 4:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   **************** {args_list[3]} looks like a legit IP Block****************\n")
            newclient = cli.file_manager.edit_freeradius_client(
                "append",
                [{'Shared Secret': args_list[4], 'IP Block': args_list[3], "Family": args_list[2]}]
            )
            if isinstance(newclient, str) and "FATAL" in newclient:
                cli.file_manager.log_write("cli", cli.ui.color(newclient, cli.ui.red))
                print("\n\n")
                cli.print_failure()
            else:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   **************** New clients added ****************\n")
                print(cli.ui.make_table(["IP Block", "Family", "Shared Secret"], cli.file_manager.get_freeradius_clients()))
                print("\n\n")
                cli.print_success()
        else:
            print("\n")
            print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   **************** Please enter a shared secret to use for this set of clients ****************\n", cli.ui.red))
            print("\n")
            cli.print_failure()
    else:
        print("\n")
        print(cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   **************** {args_list[2]} is not a legit IP family****************\n", cli.ui.red))
        print("\n")
        cli.print_failure()

    print_footer(cli, header)


def _set_target(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set the firewall target"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    configfile = cli.context.config.config_file

    # Parse hostname and vsys
    if ":" in args_list[2]:
        words = args_list[2].split(":")
        hostname = words[0]
        vsys = words[1].replace("vsys", "")
    else:
        hostname = args_list[2]
        vsys = "1"

    inputcheck = {}

    # Check hostname
    if cli.file_manager.validate_ip("address", hostname):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Hostname {hostname} looks like legit IPv4 address****************\n")
        inputcheck["hostnamecheck"] = "pass"
    else:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Hostname {hostname} looks like a domain name****************\n")
        domaincheck = cli.file_manager.validate_domain_name(hostname)
        if domaincheck["status"] == "fail":
            for message in domaincheck["messages"]:
                # Messages are strings, not dicts
                print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************ERROR: {message}****************\n", cli.ui.red))
            inputcheck["hostnamecheck"] = "fail"
        else:
            for message in domaincheck["messages"]:
                # Messages are strings - check if it's a warning
                if "warning" in message.lower():
                    print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{message}****************\n", cli.ui.yellow))
            inputcheck["hostnamecheck"] = "pass"

    # Check vsys
    try:
        vsys_int = int(vsys)
        if 1 <= vsys_int <= 255:
            inputcheck["vsyscheck"] = "pass"
        else:
            print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   **************** FATAL: Invalid VSYS ID. Please use a number between 1 and 255****************\n", cli.ui.red))
            inputcheck["vsyscheck"] = "fail"
    except ValueError:
        print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   **************** FATAL: Invalid VSYS ID. Please use a number between 1 and 255****************\n", cli.ui.red))
        inputcheck["vsyscheck"] = "fail"

    # Compile parameters
    targetparams = {'hostname': hostname, "vsys": vsys}
    searchqueries = ['username', 'password', 'port']
    cliparams = args_list[3:]

    targetindices = cli.data_processor.find_index_in_list(searchqueries, cliparams)
    for key in targetindices:
        try:
            targetparams[key] = cliparams[targetindices[key] + 1]
        except IndexError:
            print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************WARNING: You didn't enter the value for {key}****************\n", cli.ui.yellow))

    # Check username if provided
    if "username" in targetparams:
        usercheck = cli.file_manager.validate_userpass("user", targetparams["username"])
        if usercheck["status"] == "fail":
            for message in usercheck["messages"]:
                key = list(message.keys())[0]
                val = list(message.values())[0]
                if key == "FATAL":
                    print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{key}: {val}****************\n", cli.ui.red))
                elif key == "WARNING":
                    print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{key}: {val}****************\n", cli.ui.yellow))
            inputcheck["usercheck"] = "fail"
        else:
            for message in usercheck["messages"]:
                key = list(message.keys())[0]
                val = list(message.values())[0]
                if key == "WARNING":
                    print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{key}: {val}****************\n", cli.ui.yellow))
            inputcheck["usercheck"] = "pass"

    # Check password if provided
    if "password" in targetparams:
        passwordcheck = cli.file_manager.validate_userpass("password", targetparams["password"])
        if passwordcheck["status"] == "fail":
            for message in passwordcheck["messages"]:
                key = list(message.keys())[0]
                val = list(message.values())[0]
                if key == "FATAL":
                    print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{key}: {val}****************\n", cli.ui.red))
                elif key == "WARNING":
                    print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{key}: {val}****************\n", cli.ui.yellow))
            inputcheck["passwordcheck"] = "fail"
        else:
            for message in passwordcheck["messages"]:
                key = list(message.keys())[0]
                val = list(message.values())[0]
                if key == "WARNING":
                    print("\n" + cli.ui.color(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{key}: {val}****************\n", cli.ui.yellow))
            inputcheck["passwordcheck"] = "pass"

    # Evaluate input checks
    applysettings = all(v == "pass" for v in inputcheck.values())

    if applysettings:
        results = cli.config_manager.add_target([targetparams])
        if hostname in results:
            for message in results[hostname].get("messages", []):
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************{message}****************\n")
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}:   ****************Writing config change to: {configfile}****************\n")
        cli.config_manager.save()
        cli.config_manager.show_config_item('xml', "none", 'targets')

        # Republish config and scrub targets
        cli.config_manager.load(mode='quiet')
        cli.file_manager.scrub_targets("noisy", "report")
        cli.print_success()
    else:
        cli.print_failure()

    print_footer(cli, header)


def _set_munge(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set munge rule"""
    helper = "\n - set munge <rule>.<step> [parameters] |  Parameters: match (any | <regex>) (complete | partial)"\
             "\n                                        |              set-variable <variable name> (from-match | from-string) <regex or string>"\
             "\n                                        |              assemble <variable name> <variable name> ... "\
             "\n                                        |              accept"\
             "\n                                        |              discard"

    rulenum = ""
    stepnum = ""

    try:
        if "." in args_list[2]:
            rulenum = args_list[2].split(".")[0]
            stepnum = args_list[2].split(".")[1]
            if rulenum == re.findall(r'[0-9]+', rulenum)[0] and stepnum == re.findall(r'[0-9]+', stepnum)[0]:
                keepgoing = True
            else:
                print(cli.ui.color("\n\nRule and step numbers must be numerical and separated by a period (ie: set munge 1.0 ...)\n\n", cli.ui.red))
                print(helper)
                keepgoing = False

            if len(stepnum) > 1 and stepnum[0] == "0":
                print(cli.ui.color("\n\nNo leading zeros in step numbers!\n\n", cli.ui.red))
                keepgoing = False
        elif args_list[2] == 'debug':
            configinput = {'debug': None}
            cli.config_manager.set_munge_config(configinput)
            cli.config_manager.save()
            cli.config_manager.show_config_item('xml', "none", 'munge')
            return
        else:
            print(cli.ui.color("\n\nRule and step numbers must be numerical and separated by a period (ie: set munge 1.0 ...)\n\n", cli.ui.red))
            print(helper)
            keepgoing = False
    except IndexError:
        print(cli.ui.color("\n\nRule and step numbers must be numerical and separated by a period (ie: set munge 1.0 ...)\n\n", cli.ui.red))
        print(helper)
        return

    if not keepgoing:
        return

    # Handle helper messages and incomplete inputs
    acceptableactions = ['accept', 'discard', 'set-variable', 'assemble']
    acceptablepatterns = ['complete', 'partial']

    if len(args_list) == 3:
        if stepnum == "0":
            print(f"\n\n - set munge {args_list[2]} match (any | <regex pattern>) (complete | partial)\n\n")
            print("        NOTE: The match statement on the '0' step is used to determine when to process the rule")
            print("              The rule can be activated on either a partial or complete regex match\n\n")
        else:
            print(f"\n\n - set munge {args_list[2]} (accept | assemble | discard | set-variable) [parameters]\n\n")
        return

    # Various helper conditions (abbreviated for length)
    if len(args_list) == 4 and args_list[3] == "set-variable" and stepnum != "0":
        print(f"\n\n - set munge {args_list[2]} set-variable <variable name> (from-match | from-string) (any | <regex | <string>)\n\n")
        return

    if len(args_list) == 5 and args_list[3] == "match" and stepnum == "0":
        print(f"\n\n - set munge {args_list[2]} match (any | <regex pattern>) (complete | partial) \n")
        return

    # Process valid munge commands
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")
    configfile = cli.context.config.config_file

    rule = 'rule' + rulenum
    step = 'step' + stepnum
    action = args_list[3] if len(args_list) > 3 else ""

    # Check that the initial match statement exists for non-zero steps
    if stepnum != "0":
        keepgoing = False
        config_dict = cli.context.config_dict
        try:
            if config_dict and 'globalsettings' in config_dict:
                munge = config_dict['globalsettings'].get('munge', {})
                if rule in munge and 'match' in munge[rule]:
                    keepgoing = True
        except KeyError:
            pass

        if not keepgoing:
            print(cli.ui.color(f"\n\nRule does not have initial 'match' statement yet", cli.ui.red))
            print(cli.ui.color(f"\nAll rules must begin with a step '0' and a match statement (ie: 'set munge {rulenum}.0 match any')\n\n", cli.ui.red))

    if keepgoing:
        configinput = None

        if len(args_list) == 4 and stepnum != "0":
            configinput = {rule: {step: {action: None}}}
        elif len(args_list) == 5 and action == "match":
            if args_list[4] == 'any':
                configinput = {rule: {'match': {'any': None}}}
        elif len(args_list) == 6 and action == "match":
            try:
                re.findall(args_list[4], "")
                regexgood = True
            except Exception as e:
                print(cli.ui.color("\n\nInvalid regular expression. Please check it and re-enter", cli.ui.red))
                print(cli.ui.color(f"\nERROR: {str(e)}", cli.ui.red))
                regexgood = False
                keepgoing = False

            if regexgood:
                configinput = {rule: {'match': {'regex': args_list[4], 'criterion': args_list[5]}}}
        elif len(args_list) == 7 and action == 'set-variable':
            variable = args_list[4]
            sourcetype = args_list[5]
            source = args_list[6]
            if source == "any":
                configinput = {rule: {step: {sourcetype: {source: None}, action: variable}}}
            elif sourcetype == "from-string":
                configinput = {rule: {step: {sourcetype: source, action: variable}}}
            else:
                try:
                    re.findall(source, "")
                    regexgood = True
                except Exception as e:
                    print(cli.ui.color("\n\nInvalid regular expression. Please check it and re-enter", cli.ui.red))
                    print(cli.ui.color(f"\nERROR: {str(e)}", cli.ui.red))
                    regexgood = False
                    keepgoing = False

                if regexgood:
                    configinput = {rule: {step: {sourcetype: source, action: variable}}}
        elif len(args_list) > 4 and action == 'assemble':
            variables = args_list[4:]
            variablenum = 1
            configinput = {rule: {step: {'assemble': {}}}}
            for variable in variables:
                configinput[rule][step]['assemble'][f'variable{variablenum}'] = variable
                variablenum += 1

        if keepgoing and configinput:
            cli.config_manager.set_munge_config(configinput)
            cli.config_manager.save()
            cli.config_manager.show_config_item('xml', "none", 'munge')

    print("\n")
    if keepgoing:
        cli.print_success()
    else:
        cli.print_failure()

    print_footer(cli, header)


def _show_livelog_help() -> None:
    """Show help for set livelog command"""
    print("\n - set livelog <option> <value>  |  Configure live log file processing for NPS/continuously written logs")
    print("                                 |")
    print("                                 |  Options:  file <path>       - Path to the live log file being written to")
    print("                                 |            tracker <path>    - Path to the position tracker file")
    print("                                 |            enabled (on|off)  - Enable/disable live log processing")
    print("                                 |")
    print("                                 |  Examples: 'set livelog file /mnt/logs/IN2512.log'")
    print("                                 |            'set livelog tracker /var/lib/radiuid/tracker'")
    print("                                 |            'set livelog enabled on'\n")


def _set_livelog(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Set live log settings"""
    cli._log_command(arguments)
    header = print_header(cli, f"EXECUTING COMMAND: {arguments}")

    keepgoing = True

    if len(args_list) < 4:
        print(cli.ui.color("\n\nError: Missing parameters. Use 'set livelog ?' for help", cli.ui.red))
        keepgoing = False
    else:
        option = args_list[2].lower()
        value = args_list[3]

        if option == "file":
            # Validate the file path
            pathcheck = cli.file_manager.validate_path("file", value)
            if pathcheck["status"] == "fail":
                for error in pathcheck.get("errors", []):
                    print(cli.ui.color(f"...ERROR: {error}...", cli.ui.red))
                keepgoing = False
            else:
                cli.config_manager.change_config_item("livelog", "file", value)
                cli.config_manager.save()
                print(f"\nLive log file set to: {value}")

        elif option == "tracker":
            # Validate the tracker file path
            pathcheck = cli.file_manager.validate_path("file", value)
            if pathcheck["status"] == "fail":
                for error in pathcheck.get("errors", []):
                    print(cli.ui.color(f"...ERROR: {error}...", cli.ui.red))
                keepgoing = False
            else:
                cli.config_manager.change_config_item("livelog", "tracker", value)
                cli.config_manager.save()
                print(f"\nLive log tracker file set to: {value}")

        elif option == "enabled":
            if value.lower() in ("on", "true", "yes", "1"):
                cli.config_manager.change_config_item("livelog", "enabled", "true")
                cli.config_manager.save()
                print("\nLive log processing enabled")
            elif value.lower() in ("off", "false", "no", "0"):
                cli.config_manager.change_config_item("livelog", "enabled", "false")
                cli.config_manager.save()
                print("\nLive log processing disabled")
            else:
                print(cli.ui.color(f"\n\nInvalid value '{value}'. Use 'on' or 'off'", cli.ui.red))
                keepgoing = False
        else:
            print(cli.ui.color(f"\n\nUnknown option '{option}'. Use 'set livelog ?' for help", cli.ui.red))
            keepgoing = False

    print("\n")
    if keepgoing:
        cli.print_success()
    else:
        cli.print_failure()

    print_footer(cli, header)
