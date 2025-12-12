#!/usr/bin/env python3
"""
Request Commands
Handles all 'request' CLI commands for RadiUID
"""

from typing import TYPE_CHECKING, List

from ...constants import VERSION
from .helpers import print_header, print_footer

if TYPE_CHECKING:
    from ..main import CLIRouter


def handle(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Handle request commands"""

    # Request help
    if arguments == "request" or arguments == "request ?":
        _show_help()
        return

    # Request reinstall help
    if arguments in ("request reinstall", "request reinstall ?"):
        print("\n - request reinstall replace-config (no-confirm)               |     Reinstall RadiUID and REPLACE current configuration with default configuration")
        print(" - request reinstall keep-config (no-confirm)                  |     Reinstall RadiUID and KEEP current configuration with default configuration\n")
        return

    # Request uninstall help
    if arguments in ("request uninstall", "request uninstall ?"):
        print("\n - request uninstall keep-config (no-confirm)                  |     Uninstall RadiUID but KEEP configuration files")
        print(" - request uninstall remove-config (no-confirm)                |     Uninstall RadiUID and REMOVE all configuration files\n")
        return

    # Request munge-test help
    if arguments in ("request munge-test", "request munge-test ?"):
        print("\n - request munge-test <string-to-parse> (debug)\n")
        return

    # Handle specific request commands
    if len(args_list) >= 2:
        cmd = cli.cat_list(args_list[:2])

        if cmd == "request munge-test" and len(args_list) > 2:
            _request_munge_test(cli, arguments, args_list)
            return

        if cmd == "request xml-update":
            _request_xml_update(cli, arguments)
            return

        if cmd == "request auto-complete":
            _request_auto_complete(cli, arguments)
            return

        if cmd == "request freeradius-install":
            _request_freeradius_install(cli, arguments, args_list)
            return

        if cmd == "request set-mount":
            _request_set_mount(cli, arguments, args_list)
            return

    if len(args_list) >= 3:
        cmd = cli.cat_list(args_list[:3])

        if cmd == "request reinstall replace-config":
            _request_reinstall_replace(cli, arguments, args_list)
            return

        if cmd == "request reinstall keep-config":
            _request_reinstall_keep(cli, arguments, args_list)
            return

        if cmd == "request uninstall keep-config":
            _request_uninstall(cli, arguments, args_list, remove_config=False)
            return

        if cmd == "request uninstall remove-config":
            _request_uninstall(cli, arguments, args_list, remove_config=True)
            return


def _show_help() -> None:
    """Show help for request commands"""
    print("\n - request xml-update                                            |     Update the Python XML.etree modules (for compatibility on old Python versions)")
    print(" - request munge-test <string-to-parse> (debug)                  |     Test and debug the Munge Engine using a provided string")
    print(" - request auto-complete                                         |     Manually install the RadiUID BASH Auto-Completion feature")
    print(" - request freeradius-install (no-confirm)                       |     Manually install the FreeRADIUS service for use by RadiUID")
    print(" - request reinstall (replace-config | keep-config) (no-confirm) |     Reinstall RadiUID with or without replacing the current RadiUID configuration")
    print(" - request uninstall (keep-config | remove-config) (no-confirm)  |     Uninstall RadiUID from the system")
    print(" - request set-mount (<mount-path> | none)                       |     Configure network mount dependency for RadiUID service\n")


def _request_munge_test(cli: 'CLIRouter', _arguments: str, args_list: List[str]) -> None:
    """Test munge engine with a string"""
    # Check for debug flag
    if len(args_list) > 3 and args_list[3] == 'debug':
        try:
            mungeconfig = cli.context.munge_config or {}
            mungeconfig['debug'] = None
        except (NameError, AttributeError):
            pass

    header = print_header(cli, "MUNGE TEST")

    try:
        mungeconfig = cli.context.munge_config
        if mungeconfig:
            returnedstring = cli.data_processor.munge([args_list[2]], mungeconfig)[0]
            print("\n\n")
            print(f"String input from command line:  {cli.ui.color(args_list[2], cli.ui.cyan)}")
            print("\n")
            print(f"String returned by Munge Engine: {cli.ui.color(returnedstring, cli.ui.cyan)}")
        else:
            print(cli.ui.color("\n\n********** NO MUNGE RULES CURRENTLY CONFIGURED! **********\n\n", cli.ui.red))
    except (NameError, AttributeError):
        print(cli.ui.color("\n\n********** NO MUNGE RULES CURRENTLY CONFIGURED! **********\n\n", cli.ui.red))
    except IndexError:
        print(cli.ui.color("\n\nNo string returned by Munge Engine. It was discarded", cli.ui.yellow))

    print("\n\n")
    print_footer(cli, header)


def _request_xml_update(cli: 'CLIRouter', _arguments: str) -> None:
    """Update XML ETree modules"""
    from ...installer.system_setup import SystemInstaller

    header = print_header(cli, "XML ETREE UPDATE")
    print(cli.ui.color("\n\n***** This will download and install Python XML ETree module 1.3.0 from the PackeTsar site *****", cli.ui.yellow))
    input(cli.ui.color(">>>>> Hit CTRL-C to cancel or ENTER to confirm >>>>", cli.ui.yellow))

    installer = SystemInstaller(cli.context)
    installer.update_xml_etree()

    print_footer(cli, header)


def _request_auto_complete(cli: 'CLIRouter', _arguments: str) -> None:
    """Install bash auto-completion"""
    from ...installer.system_setup import SystemInstaller

    header = print_header(cli, "AUTO-COMPLETE INSTALL")

    installer = SystemInstaller(cli.context)
    installer.install_bash_completion()

    input(cli.ui.color("\nYou will need to log out and log back in to enable the RadiUID Auto-Complete feature\nHit ENTER to Complete>>>>>", cli.ui.cyan))

    print_footer(cli, header)


def _request_reinstall_replace(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Reinstall RadiUID replacing configuration"""
    from ...installer.system_setup import SystemInstaller

    confirm = True
    if len(args_list) > 3 and args_list[3].lower() == "no-confirm":
        confirm = False

    cli._log_command(arguments)

    header = print_header(cli, "RADIUID REINSTALL/UPGRADE")

    installer = SystemInstaller(cli.context)

    if confirm:
        print(cli.ui.color(f"\n\n***** Are you sure you want to re-install/upgrade RadiUID using version {VERSION}?*****", cli.ui.yellow))
        print(cli.ui.color("***** This will overwrite your current RadiUID configuration with the default configuration.*****", cli.ui.yellow))
        answer = input(cli.ui.color(">>>>> If you are sure you want to do this, type in 'CONFIRM' and hit ENTER >>>>", cli.ui.yellow))

        if answer.lower() == "confirm":
            print("\n\n****************Re-installing/upgrading the RadiUID service...****************\n")
            installer.copy_radiuid_files(replace_config=True)
            installer.install_service()

            svcctloutput = cli.service_controller.control_service("restart", "radiuid")
            print(svcctloutput.get("after", ""))

            status = svcctloutput.get("status", "")
            if status == "running":
                print(cli.ui.color("\n\n********** RADIUID STARTED UP! **********\n\n", cli.ui.green))
            elif status == "dead":
                print(cli.ui.color("\n\n********** RADIUID STARTUP UNSUCCESSFUL! **********\n\n", cli.ui.red))
            elif status == "not-found":
                print(cli.ui.color("\n\n********** LOOKS LIKE RADIUID IS NOT INSTALLED. YOU NEED TO INSTALL IT **********\n\n", cli.ui.red))

            print("\n")
            installer.install_bash_completion()
            input(cli.ui.color(">>>>> You will need to log out and log back in to activate the RadiUID CLI auto-completion functionality\n>>>>> Hit ENTER to finish\n>>>>>", cli.ui.cyan))
            cli.print_success()
        else:
            print(cli.ui.color("\n\n***** Reinstall/Upgrade of RadiUID Cancelled *****\n", cli.ui.yellow))
    else:
        print("\n\n****************Re-installing/upgrading the RadiUID service...****************\n")
        installer.copy_radiuid_files(replace_config=True)
        installer.install_service()

        svcctloutput = cli.service_controller.control_service("restart", "radiuid")
        print(svcctloutput.get("after", ""))

        status = svcctloutput.get("status", "")
        if status == "running":
            print(cli.ui.color("\n\n********** RADIUID STARTED UP! **********\n\n", cli.ui.green))
        elif status == "dead":
            print(cli.ui.color("\n\n********** RADIUID STARTUP UNSUCCESSFUL! **********\n\n", cli.ui.red))
        elif status == "not-found":
            print(cli.ui.color("\n\n********** LOOKS LIKE RADIUID IS NOT INSTALLED. YOU NEED TO INSTALL IT **********\n\n", cli.ui.red))

        print("\n")
        installer.install_bash_completion()

    print_footer(cli, header)


def _request_reinstall_keep(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Reinstall RadiUID keeping configuration"""
    from ...installer.system_setup import SystemInstaller

    confirm = True
    if len(args_list) > 3 and args_list[3].lower() == "no-confirm":
        confirm = False

    cli._log_command(arguments)

    header = print_header(cli, "RADIUID REINSTALL/UPGRADE")

    installer = SystemInstaller(cli.context)

    if confirm:
        print(cli.ui.color(f"\n\n***** Are you sure you want to re-install/upgrade RadiUID using version {VERSION}?*****", cli.ui.yellow))
        print(cli.ui.color("***** This will keep your current RadiUID configuration.*****", cli.ui.yellow))
        answer = input(cli.ui.color(">>>>> If you are sure you want to do this, type in 'CONFIRM' and hit ENTER >>>>", cli.ui.yellow))

        if answer.lower() == "confirm":
            print("\n\n****************Re-installing/upgrading the RadiUID service...****************\n")
            installer.copy_radiuid_files(replace_config=False)
            installer.install_service()

            print("\n\n****************Checking Config File Schema****************\n")
            cli.config_manager.extend_config_schema()
            cli.config_manager.save()

            print("\n")
            installer.install_bash_completion()
            input(cli.ui.color(">>>>> You will need to log out and log back in to activate the RadiUID CLI auto-completion functionality\n>>>>> Hit ENTER to finish\n>>>>>", cli.ui.cyan))
            cli.print_success()
        else:
            print(cli.ui.color("\n\n***** Reinstall/Upgrade of RadiUID Cancelled *****\n", cli.ui.yellow))
    else:
        print("\n\n****************Re-installing/upgrading the RadiUID service...****************\n")
        installer.copy_radiuid_files(replace_config=False)
        installer.install_service()

        print("\n\n****************Checking Config File Schema****************\n")
        cli.config_manager.extend_config_schema()
        cli.config_manager.save()

        print("\n")
        installer.install_bash_completion()

    print_footer(cli, header)


def _request_freeradius_install(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Install FreeRADIUS"""
    from ...installer.system_setup import SystemInstaller

    confirm = True
    if len(args_list) > 2 and args_list[2].lower() == "no-confirm":
        confirm = False

    cli._log_command(arguments)

    header = print_header(cli, "FREERADIUS MANUAL INSTALL")

    installer = SystemInstaller(cli.context)

    if confirm:
        print(cli.ui.color("\n\n***** Are you sure you want to install/reinstall FreeRADIUS?*****", cli.ui.yellow))
        answer = input(cli.ui.color(">>>>> If you are sure you want to do this, type in 'CONFIRM' and hit ENTER >>>>", cli.ui.yellow))

        if answer.lower() == "confirm":
            installer.install_freeradius()
        else:
            print(cli.ui.color("\n\n***** Install/Reinstall of FreeRADIUS Cancelled *****\n", cli.ui.yellow))
    else:
        installer.install_freeradius()

    print_footer(cli, header)


def _request_uninstall(cli: 'CLIRouter', arguments: str, args_list: List[str], remove_config: bool) -> None:
    """Uninstall RadiUID from the system"""
    from ...installer.system_setup import SystemInstaller

    confirm = True
    if len(args_list) > 3 and args_list[3].lower() == "no-confirm":
        confirm = False

    cli._log_command(arguments)

    header = print_header(cli, "RADIUID UNINSTALL")

    installer = SystemInstaller(ui=cli.ui)

    config_action = "REMOVE" if remove_config else "KEEP"

    if confirm:
        print(cli.ui.color(f"\n\n***** Are you sure you want to uninstall RadiUID? *****", cli.ui.yellow))
        print(cli.ui.color(f"***** Configuration files will be: {config_action}ED *****", cli.ui.yellow))

        if remove_config:
            print(cli.ui.color("***** WARNING: This will delete /etc/radiuid/ and all configuration! *****", cli.ui.red))

        answer = input(cli.ui.color(">>>>> If you are sure you want to do this, type in 'CONFIRM' and hit ENTER >>>>", cli.ui.yellow))

        if answer.lower() == "confirm":
            print("\n\n****************Uninstalling RadiUID...****************\n")
            success = installer.uninstall_radiuid(remove_config=remove_config)

            if success:
                print(cli.ui.color("\n\n********** RADIUID HAS BEEN UNINSTALLED **********\n", cli.ui.green))
                if not remove_config:
                    print(cli.ui.color("Configuration files preserved at /etc/radiuid/", cli.ui.cyan))
                    print(cli.ui.color("To completely remove, run: rm -rf /etc/radiuid/\n", cli.ui.cyan))
            else:
                print(cli.ui.color("\n\n********** UNINSTALL COMPLETED WITH WARNINGS **********\n", cli.ui.yellow))
                print(cli.ui.color("Some files may not have been removed. Check warnings above.\n", cli.ui.yellow))
        else:
            print(cli.ui.color("\n\n***** Uninstall of RadiUID Cancelled *****\n", cli.ui.yellow))
    else:
        print("\n\n****************Uninstalling RadiUID...****************\n")
        success = installer.uninstall_radiuid(remove_config=remove_config)

        if success:
            print(cli.ui.color("\n\n********** RADIUID HAS BEEN UNINSTALLED **********\n", cli.ui.green))
        else:
            print(cli.ui.color("\n\n********** UNINSTALL COMPLETED WITH WARNINGS **********\n", cli.ui.yellow))

    print_footer(cli, header)


def _request_set_mount(cli: 'CLIRouter', arguments: str, args_list: List[str]) -> None:
    """Configure network mount dependency for RadiUID service"""
    from ...installer.system_setup import SystemInstaller

    cli._log_command(arguments)

    header = print_header(cli, "CONFIGURE MOUNT DEPENDENCY")

    installer = SystemInstaller(ui=cli.ui)

    # Check if mount path was provided
    if len(args_list) < 3:
        print(cli.ui.color("\n\nUsage: request set-mount <mount-path> | none", cli.ui.yellow))
        print(cli.ui.color("Example: request set-mount /mnt/accountinglogs", cli.ui.yellow))
        print(cli.ui.color("         request set-mount none\n", cli.ui.yellow))
        print_footer(cli, header)
        return

    mount_path = args_list[2]

    # Handle 'none' to remove mount dependency
    if mount_path.lower() == "none":
        print(cli.ui.color("\n\n***** Removing network mount dependency from RadiUID service *****\n", cli.ui.yellow))
        installer.install_service(mount_point=None)
        print(cli.ui.color("\n********** Mount dependency removed. Service file updated. **********\n", cli.ui.green))
        print(cli.ui.color("Run 'service radiuid restart' to apply changes.\n", cli.ui.cyan))
    else:
        # Validate mount path starts with /
        if not mount_path.startswith('/'):
            print(cli.ui.color(f"\n\n***** Invalid mount path: {mount_path} *****", cli.ui.red))
            print(cli.ui.color("Mount path must be an absolute path starting with /\n", cli.ui.red))
            print_footer(cli, header)
            return

        # Convert to a systemd mount unit name for display.
        mount_unit = mount_path.strip('/').replace('/', '-') + '.mount'

        print(cli.ui.color(f"\n\n***** Configuring RadiUID service to wait for mount: {mount_path} *****\n", cli.ui.yellow))
        print(cli.ui.color(f"Systemd mount unit: {mount_unit}\n", cli.ui.cyan))

        installer.install_service(mount_point=mount_path)

        print(cli.ui.color("\n********** Mount dependency configured. Service file updated. **********\n", cli.ui.green))
        print(cli.ui.color("Run 'service radiuid restart' to apply changes.\n", cli.ui.cyan))

    print_footer(cli, header)
