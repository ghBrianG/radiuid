#!/usr/bin/env python3
"""
CLI Main Module
Entry point and command router for RadiUID CLI
"""

import sys
import os
from typing import Optional, List

from ..logging_config import get_logger
from ..context import AppContext, get_context
from ..constants import VERSION, TLSVersions
from ..ui.interface import UserInterface
from ..core.config_manager import ConfigManager
from ..core.file_manager import FileManager
from ..firewall.palo_alto import PaloAltoFirewall
from ..core.data_processor import DataProcessor
from ..installer.system_setup import ServiceController


class CLIRouter:
    """Routes CLI commands to appropriate handlers"""

    def __init__(self, context: Optional[AppContext] = None):
        self.context = context or get_context()
        self.logger = get_logger('cli')

        # Initialize components
        self.ui = UserInterface()
        self.config_manager = ConfigManager(self.context, self.ui)
        self.file_manager = FileManager(self.context, self.ui)
        self.firewall = PaloAltoFirewall(self.context, self.ui)
        self.data_processor = DataProcessor(self.context, self.ui)
        self.service_controller = ServiceController(self.context.system_info)

        # Determine how radiuid was invoked
        if "radiuid.py" in sys.argv[0]:
            self.runcmd = "python " + sys.argv[0]
        else:
            self.runcmd = "radiuid"

    def cat_list(self, listname: List[str]) -> str:
        """Create string sentence from list separated by spaces and lowercase"""
        result = ""
        for word in listname:
            result = result + word.lower() + " "
        return result.rstrip()

    def initialize(self) -> None:
        """Initialize configuration and context"""
        self.config_manager.load(mode='quiet')
        self._setup_tls()

    def _setup_tls(self) -> None:
        """Configure TLS version from context"""
        tls_version = self.context.config.tls_version
        self.context.tls_obj = TLSVersions.get_protocol(tls_version)

    def route(self, arguments: str) -> None:
        """Route arguments to appropriate command handler"""
        # Import command handlers here to avoid circular imports
        from .commands import show, set_cmd, clear, service, request

        args_list = sys.argv[1:]

        # Run command - starts main service loop
        if arguments == "run":
            from ..core.service import RadiUIDService
            service = RadiUIDService(self.context)
            service.run()
            return

        # Install command - runs installation wizard
        if arguments == "install":
            self._log_command(arguments)
            from ..installer.wizard import InstallationWizard
            print("\n\n\n")
            wizard = InstallationWizard(self.context)
            wizard.run()
            return

        # Auto-complete helper commands
        if arguments == "targets":
            self._handle_targets_autocomplete()
            return
        elif arguments == "clients":
            self._handle_clients_autocomplete()
            return
        elif arguments == "munge-rules":
            self._handle_munge_rules_autocomplete()
            return
        elif "munge-steps" in arguments:
            self._handle_munge_steps_autocomplete()
            return
        elif arguments == "test":
            print(self.context.config_dict)
            return

        # Show commands
        if arguments.startswith("show"):
            show.handle(self, arguments, args_list)
            return

        # Set commands
        if arguments.startswith("set"):
            set_cmd.handle(self, arguments, args_list)
            return

        # Push command
        if arguments.startswith("push"):
            from .commands import push
            push.handle(self, arguments, args_list)
            return

        # Tail command
        if arguments.startswith("tail"):
            from .commands import tail
            tail.handle(self, arguments, args_list)
            return

        # Clear commands
        if arguments.startswith("clear"):
            clear.handle(self, arguments, args_list)
            return

        # Edit commands
        if arguments.startswith("edit"):
            from .commands import edit
            edit.handle(self, arguments, args_list)
            return

        # Service commands
        if arguments.startswith("service"):
            service.handle(self, arguments, args_list)
            return

        # Request commands
        if arguments.startswith("request"):
            request.handle(self, arguments, args_list)
            return

        # Version command
        if arguments == "version":
            self._show_version()
            return

        # Default - show help
        self._show_help()

    def _log_command(self, arguments: str) -> None:
        """Log command execution"""
        current_user = self.service_controller.get_current_user()
        self.file_manager.log_write(
            "cli",
            f"##### COMMAND '{arguments}' ISSUED FROM CLI BY USER '{current_user}' #####"
        )

    def _handle_targets_autocomplete(self) -> None:
        """Handle targets autocomplete output"""
        try:
            for target in self.context.targets:
                print(f"{target.hostname}:vsys{target.vsys}")
        except (NameError, AttributeError):
            pass

    def _handle_clients_autocomplete(self) -> None:
        """Handle clients autocomplete output"""
        client_info = self.file_manager.get_freeradius_clients()
        if isinstance(client_info, str) and "FATAL" in client_info:
            return
        for client in client_info:
            print(client.get("IP Block", ""))

    def _handle_munge_rules_autocomplete(self) -> None:
        """Handle munge rules autocomplete output"""
        try:
            config_dict = self.context.config_dict
            if config_dict and 'globalsettings' in config_dict:
                munge = config_dict['globalsettings'].get('munge', {})
                for rulename in munge.keys():
                    print(rulename)
        except (KeyError, AttributeError):
            pass

    def _handle_munge_steps_autocomplete(self) -> None:
        """Handle munge steps autocomplete output"""
        try:
            config_dict = self.context.config_dict
            if len(sys.argv) > 2:
                rule_name = sys.argv[2]
                munge = config_dict['globalsettings']['munge']
                for stepname in munge.get(rule_name, {}).keys():
                    if stepname != "match":
                        print(stepname)
        except (KeyError, AttributeError, IndexError):
            pass

    def _show_version(self) -> None:
        """Show version information"""
        self._log_command("version")

        header = "########################## CURRENT RADIUID AND FREERADIUS VERSIONS ##########################"
        print(self.ui.color(header, self.ui.magenta))

        print("-------------------------------------- OPERATING SYSTEM --------------------------------------")
        os_version = self.context.system_info.os_version if self.context.system_info else "Unknown"
        print(f"***** Current OS is {self.ui.color(os_version, self.ui.green)}*****")
        print("----------------------------------------------------------------------------------------------\n")

        print("------------------------------------------ RADIUID -------------------------------------------")
        print(f"***** Currently running RadiUID {self.ui.color(VERSION, self.ui.green)} *****")
        print("----------------------------------------------------------------------------------------------\n")

        print("----------------------------------------- FREERADIUS -----------------------------------------")
        rad_service = self.context.system_info.radius_service_name if self.context.system_info else "radiusd"
        os.system(f"{rad_service} -v | grep ersion")
        print("----------------------------------------------------------------------------------------------\n")

        print(self.ui.color("#" * len(header), self.ui.magenta))
        print(self.ui.color("#" * len(header), self.ui.magenta))

    def _show_help(self) -> None:
        """Show help message with all available commands"""
        print(self.ui.color("\n\n\n########################## Below are the supported RadiUID Commands: ##########################", self.ui.magenta))
        print(self.ui.color("###############################################################################################\n\n", self.ui.magenta))
        print(self.ui.color(" - Usage if installed: ", self.ui.white) + self.ui.color("radiuid [arguments]", self.ui.green) + "\n")
        print(self.ui.color(" - Usage if NOT installed: ", self.ui.white) + self.ui.color("python radiuid.py [arguments]", self.ui.green) + "\n")
        print("-------------------------------------------------------------------------------------------------------------------------------")
        print("                     ARGUMENTS                    |                                  DESCRIPTIONS")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - run                                            |  Run the RadiUID main program in shell mode begin pushing User-ID information")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - install                                        |  Run RadiUID Install/Maintenance Utility")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - show log                                       |  Show the RadiUID log file")
        print(" - show acct-logs                                 |  Show the log files currently in the FreeRADIUS accounting directory")
        print(" - show livelog                                   |  Show the live log file settings (file, tracker, enabled)")
        print(" - show run (xml | set)                           |  Show the RadiUID configuration in XML format (default) or as set commands")
        print(" - show config (xml | set)                        |  Show the RadiUID configuration in XML format (default) or as set commands")
        print(" - show clients (file | table)                    |  Show the FreeRADIUS clients and config file")
        print(" - show status                                    |  Show the RadiUID and FreeRADIUS service statuses")
        print(" - show mappings (<target> | all | consistency)   |  Show the current IP-to-User mappings of one or all targets or check consistency")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - set logfile                                    |  Set the RadiUID logfile path")
        print(" - set radiuslogpath <directory path>             |  Set the path used to find FreeRADIUS accounting log files")
        print(" - set acctlogcopypath <directory path>           |  Set the path where RadiUID should copy acct log files before deletion")
        print(" - set maxloglines <number-of-lines>              |  Set the max number of lines allowed in the log ('0' turns circular logging off)")
        print(" - set userdomain (none | <domain name>)          |  Set the domain name prepended to User-ID mappings")
        print(" - set timeout                                    |  Set the timeout (in minutes) for User-ID mappings sent to the firewall targets")
        print(" - set looptime                                   |  Set the waiting loop time (in seconds) to pause between checks of the RADIUS logs")
        print(" - set tlsversion (1.0 | 1.1 | 1.2)               |  Set the version of TLS used for XML API communication with the firewall targets")
        print(" - set radiusstopaction (clear | ignore | push)   |  Set the action taken by RadiUID when RADIUS stop messages are received")
        print(" - set client (ipv4|ipv6) <ip-block> <secret>     |  Set configuration elements for RADIUS clients to send accounting data FreeRADIUS")
        print(" - set munge <rule>.<step> [parameters]           |  Set munge (string processing rules) for User-IDs")
        print(" - set target <hostname>:<vsys-id> [parameters]   |  Set configuration elements for existing or new firewall targets")
        print(" - set livelog file <path>                        |  Set the path to the live log file (NPS log being actively written)")
        print(" - set livelog tracker <path>                     |  Set the path to the tracker file (stores last read position)")
        print(" - set livelog enabled (true | false)             |  Enable or disable live log processing")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - push (<hostname>:<vsys-id> | all) [parameters] |  Manually push a User-ID mapping to one or all firewall targets")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - tail log (<# of lines>)                        |  Watch the RadiUID log file in real time")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - clear log                                      |  Delete the content in the log file")
        print(" - clear acct-logs                                |  Delete the log files currently in the FreeRADIUS accounting directory")
        print(" - clear livelog tracker                          |  Reset the live log tracker (re-read from beginning)")
        print(" - clear client (<ip-block> | all)                |  Delete one or all RADIUS client IP blocks in FreeRADIUS config file")
        print(" - clear munge (<rule> | all) (<step> | all)      |  Delete one or all munge rules in the config file")
        print(" - clear target (<hostname>:<vsys-id> | all)      |  Delete one or all firewall targets in the config file")
        print(" - clear mappings [parameters]                    |  Remove one or all IP-to-User mappings from one or all firewalls")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - edit config                                    |  Edit the RadiUID config file")
        print(" - edit clients                                   |  Edit RADIUS client config file for FreeRADIUS")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - service [parameters]                           |  Control the RadiUID and FreeRADIUS system services")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - request [parameters]                           |  Make system-level changes for RadiUID service")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(" - version                                        |  Show the current version of RadiUID and FreeRADIUS")
        print("-------------------------------------------------------------------------------------------------------------------------------\n")
        print(self.ui.color("###############################################################################################", self.ui.magenta))
        print(self.ui.color("###############################################################################################", self.ui.magenta))

    def print_header(self, text: str) -> None:
        """Print a formatted header"""
        header = f"########################## {text} ##########################"
        print(self.ui.color(header, self.ui.magenta))
        print(self.ui.color("#" * len(header), self.ui.magenta))

    def print_footer(self, header_len: int) -> None:
        """Print a formatted footer"""
        print(self.ui.color("#" * header_len, self.ui.magenta))
        print(self.ui.color("#" * header_len, self.ui.magenta))

    def print_success(self) -> None:
        """Print success message"""
        print(self.ui.color("Success!", self.ui.green))

    def print_failure(self) -> None:
        """Print failure message"""
        print(self.ui.color("Something Went Wrong!", self.ui.red))


def main() -> None:
    """Main entry point for RadiUID CLI"""
    cli = CLIRouter()
    cli.initialize()

    # Build arguments string from sys.argv
    arguments = cli.cat_list(sys.argv[1:])

    # Route to appropriate handler
    cli.route(arguments)


if __name__ == "__main__":
    main()
