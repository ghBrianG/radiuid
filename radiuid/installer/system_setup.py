#!/usr/bin/env python3
"""
System Setup Module
Handles service control and system installation tasks
"""

import os
import subprocess
import time
from typing import Dict, List, Optional, Any

from ..logging_config import get_logger
from ..system_info import get_system_info, SystemInfo
from ..templates import read_template
from ..ui.interface import UserInterface

logger = get_logger('system_setup')


def find_radiuid_executable() -> str:
    """
    Find the radiuid executable path.

    Checks common locations in order of preference:
    1. Virtual environment at /opt/radiuid
    2. /usr/local/bin (pip install)
    3. /usr/bin
    4. Current Python's bin directory

    Returns:
        The path to the radiuid executable
    """
    import shutil
    import sys

    # Check common locations in order of preference
    candidates = [
        '/opt/radiuid/bin/radiuid',  # Recommended venv location
        '/usr/local/bin/radiuid',  # System pip install
        '/usr/bin/radiuid',  # System package
        shutil.which('radiuid'),  # Search PATH
    ]

    # Also check the bin directory of the current Python interpreter
    python_bin_dir = os.path.dirname(sys.executable)
    candidates.append(os.path.join(python_bin_dir, 'radiuid'))

    for path in candidates:
        if path and os.path.isfile(path):
            return path

    # Fallback to /opt/radiuid/bin/radiuid as the recommended default
    return '/opt/radiuid/bin/radiuid'


def generate_systemd_service(mount_point: str = None, radiuid_bin: str = None) -> str:
    """
    Generate the systemd service file content.

    Args:
        mount_point: An optional mount point path (e.g., /mnt/accountinglogs).
                    If provided, adds the mount dependencies to the service file.
        radiuid_bin: Optional path to the radiuid executable. If not provided,
                    will attempt to auto-detect.

    Returns:
        The service file content as a string
    """
    if mount_point:
        # Convert the mount point to a systemd mount unit name.
        # /mnt/accountinglogs -> mnt-accountinglogs.mount
        mount_unit = mount_point.strip('/').replace('/', '-') + '.mount'

        mount_after = f" {mount_unit}"
        mount_requires = f"Requires={mount_unit}"
        mount_requires_for = f"RequiresMountsFor={mount_point}"
    else:
        mount_after = ""
        mount_requires = ""
        mount_requires_for = ""

    # Find the radiuid executable if not provided
    if radiuid_bin is None:
        radiuid_bin = find_radiuid_executable()

    template = read_template('radiuid.service.template')
    return template.format(
        mount_after=mount_after,
        mount_requires=mount_requires,
        mount_requires_for=mount_requires_for,
        radiuid_bin=radiuid_bin
    )

class ServiceController:
    """
    Controls the system services (start, stop, restart, status).
    Supports SystemD, init.d, and container environments.
    """

    def __init__(self, system_info: Optional[SystemInfo] = None, ui: Optional[UserInterface] = None):
        """
        Initialize the ServiceController.

        Args:
            system_info: A system information instance
            ui: A user interface for output
        """
        self.system_info = system_info or get_system_info()
        self.ui = ui or UserInterface()

    @staticmethod
    def get_current_user() -> str:
        """Get the currently logged-in user."""
        result = subprocess.getstatusoutput("whoami")
        return result[1]

    def get_processes(self, service_name: str) -> Dict[str, Any]:
        """
        Get the process information for a service.

        Args:
            service_name: The name of the service/process

        Returns:
            A dictionary with process information
        """
        proc_output = subprocess.getstatusoutput("ps -e")[1].splitlines()
        proc_list = []
        my_line = None
        current_pid = str(os.getpid())

        for i, line in enumerate(proc_output[1:], 1):
            parts = line.split()
            # Remove empty strings
            parts = [p for p in parts if p]
            if len(parts) >= 4:
                if parts[0] == current_pid:
                    my_line = i
                else:
                    proc_list.append(parts)

        # Find matching processes
        match_list = []
        for proc in proc_list:
            if len(proc) >= 4 and proc[3] == service_name:
                match_list.append(proc[0])

        # Build modified process data (excluding the current process)
        mod_proc_data = ""
        for i, line in enumerate(proc_output):
            if my_line is not None and i == my_line:
                continue
            mod_proc_data += line + "\n"

        return {
            'procdata': proc_output,
            'proclist': proc_list,
            'matchlist': match_list,
            'modprocdata': mod_proc_data
        }

    def control_service(self, action: str, service: str) -> Dict[str, Any]:
        """
        Control a system service.

        Args:
            action: The action to perform (start, stop, restart, status)
            service: The service name

        Returns:
            A dictionary with the command results and the status
        """
        result = {
            'beforecmd': '',
            'before': '',
            'actioncmd': '',
            'action': '',
            'aftercmd': '',
            'after': '',
            'status': 'unknown'
        }

        # Determine mode and commands based on the system type
        if self.system_info.has_systemd:
            result = self._control_systemd(action, service)
        elif self.system_info.in_container:
            result = self._control_container(action, service)
        else:
            result = self._control_initd(action, service)

        return result

    def _control_systemd(self, action: str, service: str) -> Dict[str, Any]:
        """Control a service using systemd."""
        before_cmd = f"systemctl status {service}"
        action_cmd = f"systemctl {action} {service}"
        after_cmd = f"systemctl status {service}"

        active_words = ["active (running)"]
        dead_words = ["inactive (dead)"]
        not_found_words = ["not-found"]

        # Run commands
        before = subprocess.getstatusoutput(before_cmd)
        action_result = subprocess.getstatusoutput(action_cmd)
        after = subprocess.getstatusoutput(after_cmd)

        # Determine the status
        status = self._determine_status(after[1], active_words, dead_words, not_found_words)

        return {
            'beforecmd': before_cmd,
            'before': before[1],
            'actioncmd': action_cmd,
            'action': action_result[1],
            'aftercmd': after_cmd,
            'after': after[1],
            'status': status
        }

    def _control_container(self, action: str, service: str) -> Dict[str, Any]:
        """Control a service in a container environment."""
        before_cmd = "ps -e"
        after_cmd = "ps -e"
        action_cmd = ""

        match_list = self.get_processes(service)['matchlist']
        radius_service = self.system_info.radius_service_name

        if action == "stop":
            if not match_list:
                print(self.ui.color(f"****************{service} is not running!****************\n", self.ui.red))
                action_cmd = "cd"  # A no-op
            else:
                action_cmd = "; ".join([f"kill {pid}" for pid in match_list])

        elif action == "start":
            if match_list:
                print(self.ui.color(f"****************{service} is already running! Stop it first!****************\n", self.ui.red))
                action_cmd = "cd"  # A no-op
            else:
                if service == "radiuid":
                    action_cmd = "radiuid run >> /dev/null &"
                elif service == radius_service:
                    action_cmd = radius_service

        elif action == "restart":
            if service == "radiuid":
                action_cmd = "; ".join([f"kill {pid}" for pid in match_list])
                action_cmd += "; radiuid run >> /dev/null &"
            elif service == radius_service:
                action_cmd = "; ".join([f"kill {pid}" for pid in match_list])
                action_cmd += f"; {radius_service}"

        elif action == "status":
            action_cmd = "cd"  # A no-op

        # Run commands
        before = subprocess.getstatusoutput(before_cmd)
        os.system(action_cmd)
        action_result = (0, self.get_processes(service)['modprocdata'])
        after = (0, self.get_processes(service)['modprocdata'])

        # Determine the status
        status = "dead"
        if service in after[1]:
            status = "running"

        return {
            'beforecmd': before_cmd,
            'before': before[1],
            'actioncmd': action_cmd,
            'action': action_result[1],
            'aftercmd': after_cmd,
            'after': after[1],
            'status': status
        }

    def _control_initd(self, action: str, service: str) -> Dict[str, Any]:
        """Control a service using init.d."""
        before_cmd = f"service {service} status"
        action_cmd = f"service {service} {action}"
        after_cmd = f"service {service} status"

        active_words = ["running"]
        dead_words = ["stopped", "dead"]
        not_found_words = ["unrecognized service"]

        # Run commands
        before = subprocess.getstatusoutput(before_cmd)
        action_result = subprocess.getstatusoutput(action_cmd)
        after = subprocess.getstatusoutput(after_cmd)

        # Determine the status
        status = self._determine_status(after[1], active_words, dead_words, not_found_words)

        return {
            'beforecmd': before_cmd,
            'before': before[1],
            'actioncmd': action_cmd,
            'action': action_result[1],
            'aftercmd': after_cmd,
            'after': after[1],
            'status': status
        }

    @staticmethod
    def _determine_status(output: str, active_words: List[str], dead_words: List[str], not_found_words: List[str]) -> str:
        """Determine the service status from the command output."""
        status = "unknown"

        for word in dead_words:
            if word in output:
                status = "dead"

        for word in active_words:
            if word in output:
                status = "running"

        for word in not_found_words:
            if word in output:
                status = "not-found"

        return status


class SystemInstaller:
    """
    Handles the RadiUID installation and setup tasks.
    """

    # Installation paths
    CONFIG_PATH = "/etc/radiuid/"
    BIN_PATH = "/bin/"
    SYSTEMD_PATH = "/etc/systemd/system/radiuid.service"
    INITD_PATH = "/etc/init.d/radiuid"
    BASH_COMPLETION_PATH = "/etc/bash_completion.d/radiuid"

    def __init__(
        self,
        system_info: Optional[SystemInfo] = None,
        service_controller: Optional[ServiceController] = None,
        ui: Optional[UserInterface] = None
    ):
        """
        Initialize SystemInstaller.

        Args:
            system_info: System information instance
            service_controller: Service controller instance
            ui: User interface for output
        """
        self.system_info = system_info or get_system_info()
        self.service_controller = service_controller or ServiceController(self.system_info)
        self.ui = ui or UserInterface()

    def copy_radiuid_files(self, replace_config: bool = True) -> None:
        """
        Copy the RadiUID files to the system paths.

        Args:
            replace_config: Whether to replace the existing config file
        """
        # Create the config directory
        os.makedirs(self.CONFIG_PATH, exist_ok=True)

        # Copy the config file if requested
        if replace_config:
            # Look for the config file in various locations
            config_sources = [
                'radiuid.yaml',
                'examples/radiuid.yaml.sample',
                'radiuid.conf',  # Legacy fallback
            ]
            for source in config_sources:
                if os.path.exists(source):
                    os.system(f'cp {source} {self.CONFIG_PATH}radiuid.yaml')
                    break

        # Copy the main script
        if os.path.exists('radiuid.py'):
            os.system(f'cp radiuid.py {self.BIN_PATH}radiuid')
            os.system(f'chmod 777 {self.BIN_PATH}radiuid')

        self.ui.progress("Copying Files: ", 2)

    def install_service(self, mount_point: str = None) -> None:
        """
        Install RadiUID as a system service.

        Args:
            mount_point: An optional network mount point path (e.g., /mnt/accountinglogs).
                        If provided, the service will wait for the mount before starting.
        """
        if self.system_info.has_systemd:
            install_path = self.SYSTEMD_PATH
            install_content = generate_systemd_service(mount_point)
        else:
            install_path = self.INITD_PATH
            install_content = read_template('radiuid.init')

        self.ui.progress("Installing: ", 2)

        # Write the service file
        with open(install_path, 'w') as f:
            f.write(install_content)

        # Reload systemd to pick up the changes
        if self.system_info.has_systemd:
            os.system('systemctl daemon-reload')
            os.system('systemctl enable radiuid')
        else:
            os.system('chmod 777 /etc/init.d/radiuid')
            os.system('chkconfig radiuid on')

    def install_bash_completion(self) -> None:
        """Install the bash completion script for the RadiUID CLI."""
        completion_script = self._get_bash_completion_script()

        try:
            os.makedirs(os.path.dirname(self.BASH_COMPLETION_PATH), exist_ok=True)
            with open(self.BASH_COMPLETION_PATH, 'w') as f:
                f.write(completion_script)
            os.system(f'chmod 777 {self.BASH_COMPLETION_PATH}')
            print(self.ui.color("Bash completion installed successfully", self.ui.green))
        except Exception as e:
            print(self.ui.color(f"Failed to install bash completion: {e}", self.ui.red))

    def uninstall_radiuid(self, remove_config: bool = False) -> bool:
        """
        Uninstall RadiUID from the system.

        Args:
            remove_config: Whether to remove the configuration files

        Returns:
            True on success, False on failure
        """
        success = True

        # Stop the service first
        print("Stopping RadiUID service...")
        self.service_controller.control_service("stop", "radiuid")
        self.ui.progress("Stopping Service: ", 1)

        # Disable the service
        print("Disabling RadiUID service...")
        if self.system_info.has_systemd:
            os.system('systemctl disable radiuid 2>/dev/null')
        else:
            os.system('chkconfig radiuid off 2>/dev/null')
        self.ui.progress("Disabling Service: ", 1)

        # Remove the service file
        print("Removing service file...")
        if os.path.exists(self.SYSTEMD_PATH):
            try:
                os.remove(self.SYSTEMD_PATH)
            except OSError as e:
                print(self.ui.color(f"Warning: Could not remove {self.SYSTEMD_PATH}: {e}", self.ui.yellow))
                success = False

        if os.path.exists(self.INITD_PATH):
            try:
                os.remove(self.INITD_PATH)
            except OSError as e:
                print(self.ui.color(f"Warning: Could not remove {self.INITD_PATH}: {e}", self.ui.yellow))
                success = False

        # Reload systemd
        if self.system_info.has_systemd:
            os.system('systemctl daemon-reload')
        self.ui.progress("Removing Service Files: ", 1)

        # Remove the main executable
        print("Removing RadiUID executable...")
        bin_path = os.path.join(self.BIN_PATH, "radiuid")
        if os.path.exists(bin_path):
            try:
                os.remove(bin_path)
            except OSError as e:
                print(self.ui.color(f"Warning: Could not remove {bin_path}: {e}", self.ui.yellow))
                success = False
        self.ui.progress("Removing Executable: ", 1)

        # Remove the bash completion
        print("Removing bash completion...")
        if os.path.exists(self.BASH_COMPLETION_PATH):
            try:
                os.remove(self.BASH_COMPLETION_PATH)
            except OSError as e:
                print(self.ui.color(f"Warning: Could not remove {self.BASH_COMPLETION_PATH}: {e}", self.ui.yellow))
                success = False
        self.ui.progress("Removing Bash Completion: ", 1)

        # Optionally remove config directory
        if remove_config:
            print("Removing the configuration files...")
            if os.path.exists(self.CONFIG_PATH):
                import shutil
                try:
                    shutil.rmtree(self.CONFIG_PATH)
                except OSError as e:
                    print(self.ui.color(f"Warning: Could not remove {self.CONFIG_PATH}: {e}", self.ui.yellow))
                    success = False
            self.ui.progress("Removing Configuration: ", 1)
        else:
            print(self.ui.color(f"The configuration is preserved at {self.CONFIG_PATH}", self.ui.cyan))

        return success

    def install_freeradius(self) -> str:
        """
        Install the FreeRADIUS server.

        Returns:
            'PASS' on success, 'FAIL' on failure
        """
        pkg_manager = self.system_info.package_manager

        print(f"Installing FreeRADIUS using {pkg_manager}...")
        os.system(f'{pkg_manager} install freeradius -y')

        # Refresh the service name detection
        self.system_info.refresh()
        radius_service = self.system_info.radius_service_name

        # Start the service
        self.service_controller.control_service("start", radius_service)
        time.sleep(3)

        # Check if it is running
        status = self.service_controller.control_service("status", radius_service)
        if status['status'] == "running":
            print(self.ui.color("****************FreeRADIUS is Now Running!****************", self.ui.green))
            return "PASS"
        else:
            print(self.ui.color("****************Something went wrong with the FreeRADIUS install****************", self.ui.red))
            print(self.ui.color("****************You may need to run some system updates for it to install correctly****************", self.ui.red))
            return "FAIL"

    def update_xml_etree(self) -> None:
        """
        Update XML ETree module (legacy compatibility method).

        This was used to update the XML ETree module on older Python versions.
        With Python 3.8+, this is no longer needed as the standard library
        includes an up-to-date ElementTree implementation.
        """
        print(self.ui.color("\n***** XML ETree update is no longer needed with Python 3.8+ *****", self.ui.green))
        print(self.ui.color("***** The standard library includes an up-to-date ElementTree implementation *****\n", self.ui.green))

    def _get_bash_completion_script(self) -> str:
        """Get the bash completion script content from the template file."""
        return read_template('bash_completion.sh')
