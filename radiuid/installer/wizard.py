#!/usr/bin/env python3
"""
Installation Wizard
Interactive wizard for RadiUID installation and configuration
"""

import os
import sys
from typing import Optional, List, Dict, Any

from ..logging_config import get_logger
from ..context import AppContext, get_context
from ..constants import VERSION
from ..ui.interface import UserInterface
from ..core.config_manager import ConfigManager
from ..core.file_manager import FileManager
from .system_setup import ServiceController, SystemInstaller


class InstallationWizard:
    """Interactive installation wizard for RadiUID"""

    def __init__(self, context: Optional[AppContext] = None):
        self.context = context or get_context()
        self.logger = get_logger('installer.wizard')

        # Initialize components
        self.ui = UserInterface()
        self.config_manager = ConfigManager(self.context, self.ui)
        self.file_manager = FileManager(self.context, self.ui)
        self.service_controller = ServiceController(self.context)
        self.installer = SystemInstaller(self.context)

    def run(self) -> None:
        """Run the installation wizard"""
        self._show_banner()
        self._check_python_version()
        self._check_freeradius()
        self._check_radiuid()
        self._configure_radiuid()
        self._configure_freeradius()
        self._show_trailer()

    def _show_banner(self) -> None:
        """Show the installation banner"""
        self.ui.packetsar()
        self.ui.progress("Running RadiUID in Install/Maintenance Mode:", 3)
        print("\n\n\n\n\n\n\n\n")
        print('                       ##########################################################'
              '\n' + '                       ##### Install/Maintenance Utility for RadiUID Server #####'
              '\n' + '                       #####                 Version ' + VERSION + '                  #####'
              '\n' + '                       #####             Please Use Carefully!              #####'
              '\n' + '                       ##########################################################'
              '\n' + '                       ##########################################################'
              '\n' + '                       ##########################################################'
              '\n' + '                       ##########       Written by John W Kerns        ##########'
              '\n' + '                       ##########      http://blog.packetsar.com       ##########'
              '\n' + '                       ########## https://github.com/PackeTsar/radiuid ##########'
              '\n' + '                       ##########################################################'
              '\n' + '                       ##########################################################'
              '\n' + '                       ##########################################################')

        print("\n\n\n")
        print("****************First, we will check if FreeRADIUS and RadiUID are installed yet...****************\n")
        input(self.ui.color("\n\n>>>>> Hit ENTER to continue...\n\n>>>>>", self.ui.cyan))
        print("\n\n\n\n\n\n\n")

    def _check_freeradius(self) -> None:
        """Check and install FreeRADIUS if needed"""
        print("\n\n\n\n\n\n****************Checking if FreeRADIUS is installed...****************\n")

        radservicename = self.context.system_info.radius_service_name if self.context.system_info else "radiusd"
        radcheck = self.service_controller.control_service("status", radservicename)

        if radcheck["status"] == "running":
            print(self.ui.color("***** Looks like the FreeRADIUS service is already installed and running...skipping the install of FreeRADIUS", self.ui.green))

        elif radcheck["status"] == "dead":
            freeradiusrestart = self.ui.yesorno("Looks like FreeRADIUS is installed, but not running....want to start it up?")
            if freeradiusrestart == 'yes':
                radcheck = self.service_controller.control_service("start", radservicename)
                if radcheck["status"] == "dead":
                    print(self.ui.color("***** It looks like FreeRADIUS failed to start up. You may need to change its settings and restart it manually...", self.ui.red))
                    print(self.ui.color("***** Use the command 'radiuid edit clients' to open and edit the FreeRADIUS client settings file manually", self.ui.red))
                if radcheck["status"] == "running":
                    print(self.ui.color("***** Very nice....Great Success!!!", self.ui.green))
            if freeradiusrestart == 'no':
                print(self.ui.color("~~~ OK, leaving it off...", self.ui.yellow))

        elif radcheck["status"] in ("not-found", "unknown"):
            freeradiusinstall = self.ui.yesorno(
                "Looks like FreeRADIUS is not installed. It is required by RadiUID. Is it ok to install FreeRADIUS?")
            if freeradiusinstall == 'yes':
                result = self.installer.install_freeradius()
                if result == "FAIL":
                    print(self.ui.color("\n\n***** Uh Oh... Looks like the FreeRADIUS service failed to install or start up.", self.ui.red))
                    print(self.ui.color("***** It is possible that the native package manager is not able to download the install files.", self.ui.red))
                    print(self.ui.color("***** Make sure that you have internet access and your package manager is able to download the FreeRADIUS install files", self.ui.red))
                    input(self.ui.color("Hit ENTER to quit the program...\n", self.ui.cyan))
                    quit()
                elif result == "PASS":
                    print(self.ui.color("\n\n***** Great Success!! Looks like FreeRADIUS installed and started up successfully.", self.ui.green))
                    print(self.ui.color("***** We will be adding client IP and shared secret info to FreeRADIUS later in this wizard.", self.ui.green))
                    print(self.ui.color("***** If you need to edit the FreeRADIUS clients later, you can use 'set clients' and 'clear clients' in the CLI", self.ui.green))
                    print(self.ui.color("***** You can also manually open the file for editing. It is located at /etc/raddb/clients.conf", self.ui.green))
                    input(self.ui.color("\n***** Hit ENTER to continue...\n\n>>>>>", self.ui.cyan))
            if freeradiusinstall == 'no':
                print(self.ui.color("***** FreeRADIUS is required by RadiUID. Quitting the installer", self.ui.red))
                quit()

    def _check_radiuid(self) -> None:
        """Check and install RadiUID if needed"""
        print("\n\n\n\n\n\n****************Checking if RadiUID is already installed...****************\n")

        uidcheck = self.service_controller.control_service("status", "radiuid")
        radiuidreinstall = 'no'

        if uidcheck["status"] == "running":
            print(self.ui.color("***** Looks like the RadiUID service is already installed and running...skipping the install of RadiUID\n", self.ui.green))
            radiuidreinstall = self.ui.yesorno("Do you want to re-install the RadiUID service?")

        elif uidcheck["status"] == "dead":
            print(self.ui.color("\n***** Looks like RadiUID is installed, but not running....", self.ui.yellow))
            radiuidrestart = self.ui.yesorno("Do you want to start it up?")
            if radiuidrestart == 'yes':
                uidcheck = self.service_controller.control_service("start", "radiuid")
                self.ui.progress('Checking for Successful Startup', 3)
                if uidcheck["status"] == "running":
                    print(self.ui.color("***** Great Success!!! Successful startup of RadiUID", self.ui.green))
                    radiuidreinstall = self.ui.yesorno("Do you want to re-install the RadiUID service?")
                if uidcheck["status"] != "running":
                    print(self.ui.color("***** Looks like the startup failed...", self.ui.red))
                    radiuidreinstall = self.ui.yesorno("Do you want to re-install the RadiUID service?")
            elif radiuidrestart == 'no':
                print(self.ui.color("~~~ OK, leaving it off...", self.ui.yellow))
                radiuidreinstall = self.ui.yesorno("Do you want to re-install the RadiUID service?")
        else:
            print(self.ui.color("***** Looks like RadiUID is not yet installed...", self.ui.yellow))
            radiuidreinstall = self.ui.yesorno("Do you want to install the RadiUID service?")

        if radiuidreinstall == 'yes':
            print("\n\n****************Installing the RadiUID service...****************\n")
            self.installer.copy_radiuid("replace-config")

            # Ask about network mount dependency
            mount_point = self._ask_network_mount()

            self.installer.install_service(mount_point=mount_point)
            print("\n")
            self.installer.install_radiuid_completion()
            input(self.ui.color(">>>>> You will need to log out and log back in to activate the RadiUID CLI auto-completion functionality\n>>>>>", self.ui.cyan))
            print("\n\n****************We will start up the RadiUID service once we configure the .conf file****************\n")

    def _check_python_version(self) -> None:
        """Check Python version meets minimum requirements"""
        print("\n\n\n\n")
        print("****************Checking Python version****************\n")

        major, minor, micro = sys.version_info[:3]
        version_str = f"{major}.{minor}.{micro}"

        # Minimum required: Python 3.8
        min_major, min_minor = 3, 8

        if major < min_major or (major == min_major and minor < min_minor):
            print(self.ui.color(f"***** WARNING: Python {version_str} detected.", self.ui.red))
            print(self.ui.color(f"***** RadiUID requires Python {min_major}.{min_minor} or higher.", self.ui.red))
            print(self.ui.color("***** Some features may not work correctly.", self.ui.red))
            input(self.ui.color("\nHit ENTER to continue anyway, or CTRL-C to quit...\n>>>>>", self.ui.cyan))
        else:
            print(self.ui.color(f"***** Python {version_str} detected - OK!", self.ui.green))

    def _configure_radiuid(self) -> None:
        """Configure RadiUID settings"""
        print("\n\n\n\n")
        editradiuidconf = self.ui.yesorno("Do you want to edit the settings in the RadiUID .conf file (if you just installed or reinstalled RadiUID, then you should do this)?")

        if editradiuidconf != "yes":
            print("~~~ OK... Leaving the .conf file alone")
            return

        # Load current config
        self.config_manager.load(mode='quiet')
        configfile = self.context.config.config_file

        print(f"Configuring File: {self.ui.color(configfile, self.ui.green)}\n")
        print(f"\n\n\n****************Now, we will import the settings from the {configfile} file...****************\n")
        print("*****************The current values for each setting are [displayed in the prompt]****************\n")
        print("****************Leave the prompt empty and hit ENTER to accept the current value****************\n")
        input(self.ui.color("\n\n>>>>> Hit ENTER to continue...\n\n>>>>>", self.ui.cyan))
        print("\n\n\n\n\n\n\n")
        print(f"**************** Reading in current settings from {configfile} ****************\n")
        self.ui.progress('Reading:', 1)

        # Ask questions for settings
        print("\n\n\n\n\n\n****************Please enter values for the different settings in the radiuid.conf file****************\n")

        logfile = self.context.config.log_file
        newlogfile = self._change_setting(logfile, 'Enter full path to the new RadiUID Log File')
        print("\n")

        radservicename = self.context.system_info.radius_service_name if self.context.system_info else "radiusd"
        raddirname = "radius" if radservicename == "radiusd" else radservicename
        radiuslogpath = f"/var/log/{raddirname}/radacct/"
        newradiuslogpath = self._change_setting(radiuslogpath, 'Enter path to the FreeRADIUS Accounting Logs')
        print("\n")

        userdomain = self.context.config.user_domain or ""
        newuserdomain = self._change_setting(userdomain, 'Enter the user domain to be prefixed to User-IDs')
        print("\n")

        timeout = str(self.context.config.timeout)
        newtimeout = self._change_setting(timeout, 'Enter timeout period for pushed UIDs (in minutes)')

        # Ask about targets
        print("\n****************Checking for already configured firewall targets****************\n")
        self.ui.progress('Reading:', 1)

        targets = self.context.targets or []
        if targets:
            self.file_manager.scrub_targets("noisy", "scrub")
            target_dicts = [{"hostname": t.hostname, "vsys": t.vsys, "username": t.username, "password": t.password} for t in targets]
            print(self.ui.make_table(["hostname", "vsys", 'username', 'password'], target_dicts))
        else:
            print(self.ui.color("\n****************No firewall targets currently configured****************\n", self.ui.yellow))

        print("\n\n")
        changetargets = self.ui.yesorno("Do you want to delete any current targets and set up new ones?")

        if changetargets == 'no':
            print("~~~ OK. Leaving current targets alone...")
            newtargets = target_dicts if targets else []
        else:
            anothertarget = 'yes'
            newtargets = []
            while anothertarget == 'yes':
                print("\n\n\n")
                addhostname = self._change_setting('192.168.1.1', 'Enter the IP ADDRESS or HOSTNAME of the target firewall to recieve User-ID mappings')
                addvsys = self._change_setting('vsys1', 'Enter the Virtual System ID of the target firewall to recieve User-ID mappings').replace("vsys", "")
                addusername = self._change_setting('admin', 'Enter the administrative USERNAME to use for authentication against the firewall')
                addpassword = self._change_setting('admin', 'Enter the PASSWORD for the username you just entered')
                newtargets.append({'hostname': addhostname, 'vsys': addvsys, 'username': addusername, 'password': addpassword})
                print("\n\n")
                anothertarget = self.ui.yesorno("Do you want to add another target firewall?")

            print("\n****************New Targets Are:****************\n")
            print(self.ui.make_table(["hostname", "vsys", 'username', 'password'], newtargets))
            print("\n\n\n")

        input(self.ui.color("\n\n>>>>> Hit ENTER to see what the new config will look like...\n\n>>>>>", self.ui.cyan))
        print("\n\n\n")

        # Apply settings
        self.config_manager.set_config_item('logfile', newlogfile)
        self.config_manager.set_config_item('radiuslogpath', newradiuslogpath)
        self.config_manager.set_config_item('userdomain', newuserdomain if newuserdomain else None)
        self.config_manager.set_config_item('timeout', newtimeout)

        # Apply target settings
        self.config_manager.clear_targets()
        if newtargets:
            self.config_manager.add_target(newtargets)

        # Show config
        self.config_manager.show_config_item('xml', "none", 'config')
        print("\n\n\n")

        # Apply settings
        applysettings = self.ui.yesorno("Do you want to apply your entered settings to the config file and restart the RadiUID service?")
        if applysettings == 'no':
            print("~~~ OK. Disregarding config changes...")
        else:
            print("\n\n\n\n\n\n****************Applying entered settings into the radiuid.conf file...****************\n")
            self.ui.progress('Applying:', 1)
            self.config_manager.save()

            newlogfiledir = self.file_manager.strip_filepath(newlogfile)[0]
            print(f"\n\n****************Creating log directory: {newlogfiledir}****************\n")
            os.system(f'mkdir -p {newlogfiledir}')

            print("\n\n****************Starting/Restarting the RadiUID service...****************\n")
            radiuidrunning = self.service_controller.control_service("restart", "radiuid")

            if radiuidrunning["status"] == "running":
                print(self.ui.color("***** RadiUID successfully started up!!!", self.ui.green))
                input(self.ui.color(">>>>> Hit ENTER to continue...\n\n>>>>>", self.ui.cyan))
            else:
                print(self.ui.color("***** Something went wrong. Looks like the installation or startup failed... ", self.ui.red))
                print(self.ui.color("***** Please make sure you are installing RadiUID on a support platform", self.ui.red))
                print(self.ui.color("***** You can manually edit the RadiUID config file by entering 'radiuid edit config' in the CLI", self.ui.red))
                input(self.ui.color("Hit ENTER to quit the program...\n\n>>>>>", self.ui.cyan))
                quit()

    def _configure_freeradius(self) -> None:
        """Configure FreeRADIUS clients"""
        print("\n\n\n\n\n\n****************Let's make some changes to the FreeRADIUS client config file****************\n")
        editfreeradius = self.ui.yesorno("Do you want to make changes to FreeRADIUS by adding some IP blocks for accepted accounting clients?")

        if editfreeradius == "yes":
            freeradiusedits = self._freeradius_create_changes()
            self._freeradius_apply_changes(freeradiusedits)

    def _show_trailer(self) -> None:
        """Show the trailer/goodbye message"""
        print("\n\n\n\n\n\n***** Thank you for using the RadiUID installer/management utility")
        input(self.ui.color(">>>>> Hit ENTER to see the tail of the RadiUID log file before you exit the utility\n\n>>>>>", self.ui.cyan))

        # Reload config to get logfile path
        self.config_manager.load(mode='quiet')
        logfile = self.context.config.log_file

        print(f"\n\n############################## LAST 50 LINES FROM {logfile}##############################")
        print("########################################################################################################")
        os.system(f"tail -n 50 {logfile}")
        print("########################################################################################################")
        print("########################################################################################################")
        print("\n\n\n\n***** Looks like we are all done here...\n")
        input(self.ui.color(">>>>> Hit ENTER to exit the Install/Maintenance Utility\n\n>>>>>", self.ui.cyan))
        quit()

    def _change_setting(self, current_value: str, prompt: str) -> str:
        """Prompt for a setting change"""
        result = input(f"===== {prompt} [{current_value}]: ").strip()
        if not result:
            return current_value
        return result

    def _ask_network_mount(self) -> Optional[str]:
        """
        Ask if log files are on a network share and get mount point.

        Returns:
            Mount point path (e.g., /mnt/accountinglogs) or None if not using network mount
        """
        print("\n\n****************Network Mount Configuration****************\n")
        print("If your log files (NPS/RADIUS logs) are stored on a network share,")
        print("RadiUID can wait for the mount to be available before starting.\n")

        use_mount = self.ui.yesorno("Are your log files on a network share/mount?")

        if use_mount != 'yes':
            print("~~~ OK, no mount dependency will be configured...")
            return None

        print("\n")
        print("Enter the mount point path where the network share is mounted.")
        print("This should be the directory path, not the log file path.")
        print("Example: /mnt/accountinglogs or /mnt/nps_logs\n")

        mount_point = input("===== Enter mount point path [/mnt/accountinglogs]: ").strip()

        if not mount_point:
            mount_point = "/mnt/accountinglogs"

        # Validate mount point format
        if not mount_point.startswith('/'):
            print(self.ui.color("***** Warning: Mount point should be an absolute path starting with /", self.ui.yellow))
            mount_point = '/' + mount_point

        print(f"\n{self.ui.color('***** Mount dependency configured:', self.ui.green)} {mount_point}")
        print("RadiUID service will wait for this mount before starting.\n")

        return mount_point

    def _freeradius_create_changes(self) -> List[Dict[str, str]]:
        """Create FreeRADIUS client changes"""
        anotherclient = 'yes'
        newclients = []

        while anotherclient == 'yes':
            print("\n\n\n")
            addip = self._change_setting('10.0.0.0/8', 'Enter the IP block (or single address) allowed to send accounting data to FreeRADIUS')
            addfamily = self._change_setting('ipv4', 'Enter the IP Family (ipv4 or ipv6)')
            addsecret = self._change_setting('secretpassword', 'Enter the shared secret which will be used to authenticate the client(s)')
            newclients.append({'IP Block': addip, 'Family': addfamily, 'Shared Secret': addsecret})
            print("\n\n")
            anotherclient = self.ui.yesorno("Do you want to add another client IP block?")

        print("\n****************New Clients Are:****************\n")
        print(self.ui.make_table(["IP Block", "Family", "Shared Secret"], newclients))

        return newclients

    def _freeradius_apply_changes(self, clients: List[Dict[str, str]]) -> None:
        """Apply FreeRADIUS client changes"""
        print("\n\n")
        applyclients = self.ui.yesorno("Do you want to apply these client settings to the FreeRADIUS config file?")

        if applyclients == 'no':
            print("~~~ OK. Disregarding client changes...")
        else:
            print("\n\n****************Applying client settings to FreeRADIUS config...****************\n")
            for client in clients:
                self.file_manager.edit_freeradius_client("append", [client])
            print(self.ui.color("***** Client settings applied successfully!", self.ui.green))
