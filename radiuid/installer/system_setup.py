#!/usr/bin/env python3
"""
System Setup Module
Handles service control and system installation tasks
"""

import os
import time
import subprocess
from typing import Dict, List, Optional, Any

from ..context import AppContext, get_context
from ..system_info import get_system_info, SystemInfo
from ..logging_config import get_logger
from ..ui.interface import UserInterface

logger = get_logger('system_setup')


# Service file templates
SYSTEMD_SERVICE_TEMPLATE = '''[Unit]
Description=RadiUID User-ID Service
After=network-online.target{mount_after}
{mount_requires}
{mount_requires_for}

[Service]
Type=simple
ExecStart=/usr/bin/python3 /bin/radiuid run
Restart=on-failure
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target'''


def generate_systemd_service(mount_point: str = None) -> str:
    """
    Generate systemd service file content.

    Args:
        mount_point: Optional mount point path (e.g., /mnt/accountinglogs)
                    If provided, adds mount dependencies to service file

    Returns:
        Service file content as string
    """
    if mount_point:
        # Convert mount point to systemd mount unit name
        # /mnt/accountinglogs -> mnt-accountinglogs.mount
        mount_unit = mount_point.strip('/').replace('/', '-') + '.mount'

        mount_after = f" {mount_unit}"
        mount_requires = f"Requires={mount_unit}"
        mount_requires_for = f"RequiresMountsFor={mount_point}"
    else:
        mount_after = ""
        mount_requires = ""
        mount_requires_for = ""

    return SYSTEMD_SERVICE_TEMPLATE.format(
        mount_after=mount_after,
        mount_requires=mount_requires,
        mount_requires_for=mount_requires_for
    )

INITD_SERVICE_FILE = '''#!/bin/bash
# radiuid daemon
# chkconfig: 345 20 80
# description: RADIUS to Palo-Alto User-ID Engine
# processname: radiuid

DAEMON_PATH="/bin/"

DAEMON=radiuid
DAEMONOPTS="run"

NAME=RadiUID
DESC="RADIUS to Palo-Alto User-ID Engine"
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME

case "$1" in
start)
    printf "%-50s" "Starting $NAME..."
    cd $DAEMON_PATH
    PID=`$DAEMON $DAEMONOPTS > /dev/null 2>&1 & echo $!`
    if [ -z $PID ]; then
        printf "%s\\n" "Fail"
    else
        echo $PID > $PIDFILE
        printf "%s\\n" "Ok"
    fi
;;
status)
    if [ -f $PIDFILE ]; then
        PID=`cat $PIDFILE`
        if [ -z "`ps axf | grep ${PID} | grep -v grep`" ]; then
            printf "%s\\n" "Process dead but pidfile exists"
        else
            echo "$DAEMON (pid $PID) is running..."
        fi
    else
        printf "%s\\n" "$DAEMON is stopped"
    fi
;;
stop)
    printf "%-50s" "Stopping $NAME"
    PID=`cat $PIDFILE`
    cd $DAEMON_PATH
    if [ -f $PIDFILE ]; then
        kill -HUP $PID
        printf "%s\\n" "Ok"
        rm -f $PIDFILE
    else
        printf "%s\\n" "pidfile not found"
    fi
;;

restart)
    $0 stop
    $0 start
;;

*)
    echo "Usage: $0 {status|start|stop|restart}"
    exit 1
esac'''


class ServiceController:
    """
    Controls system services (start, stop, restart, status).
    Supports SystemD, init.d, and container environments.
    """

    def __init__(self, system_info: Optional[SystemInfo] = None, ui: Optional[UserInterface] = None):
        """
        Initialize ServiceController.

        Args:
            system_info: System information instance
            ui: User interface for output
        """
        self.system_info = system_info or get_system_info()
        self.ui = ui or UserInterface()

    @staticmethod
    def get_current_user() -> str:
        """Get the currently logged in user."""
        result = subprocess.getstatusoutput("whoami")
        return result[1]

    def get_processes(self, service_name: str) -> Dict[str, Any]:
        """
        Get process information for a service.

        Args:
            service_name: Name of the service/process

        Returns:
            Dictionary with process information
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

        # Build modified process data (excluding current process)
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
            action: Action to perform (start, stop, restart, status)
            service: Service name

        Returns:
            Dictionary with command results and status
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

        # Determine mode and commands based on system type
        if self.system_info.has_systemd:
            result = self._control_systemd(action, service)
        elif self.system_info.in_container:
            result = self._control_container(action, service)
        else:
            result = self._control_initd(action, service)

        return result

    def _control_systemd(self, action: str, service: str) -> Dict[str, Any]:
        """Control service using systemd."""
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

        # Determine status
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
        """Control service in a container environment."""
        before_cmd = "ps -e"
        after_cmd = "ps -e"
        action_cmd = ""

        match_list = self.get_processes(service)['matchlist']
        radius_service = self.system_info.radius_service_name

        if action == "stop":
            if not match_list:
                print(self.ui.color(f"****************{service} is not running!****************\n", self.ui.red))
                action_cmd = "cd"  # No-op
            else:
                action_cmd = "; ".join([f"kill {pid}" for pid in match_list])

        elif action == "start":
            if match_list:
                print(self.ui.color(f"****************{service} is already running! Stop it first!****************\n", self.ui.red))
                action_cmd = "cd"  # No-op
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
            action_cmd = "cd"  # No-op

        # Run commands
        before = subprocess.getstatusoutput(before_cmd)
        os.system(action_cmd)
        action_result = (0, self.get_processes(service)['modprocdata'])
        after = (0, self.get_processes(service)['modprocdata'])

        # Determine status
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
        """Control service using init.d."""
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

        # Determine status
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
        """Determine service status from command output."""
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
    Handles RadiUID installation and setup tasks.
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
        Copy RadiUID files to system paths.

        Args:
            replace_config: Whether to replace existing config file
        """
        # Create config directory
        os.makedirs(self.CONFIG_PATH, exist_ok=True)

        # Copy config file if requested
        if replace_config and os.path.exists('radiuid.conf'):
            os.system(f'cp radiuid.conf {self.CONFIG_PATH}radiuid.conf')

        # Copy main script
        if os.path.exists('radiuid.py'):
            os.system(f'cp radiuid.py {self.BIN_PATH}radiuid')
            os.system(f'chmod 777 {self.BIN_PATH}radiuid')

        self.ui.progress("Copying Files: ", 2)

    def install_service(self, mount_point: str = None) -> None:
        """
        Install RadiUID as a system service.

        Args:
            mount_point: Optional network mount point path (e.g., /mnt/accountinglogs)
                        If provided, service will wait for mount before starting
        """
        if self.system_info.has_systemd:
            install_path = self.SYSTEMD_PATH
            install_content = generate_systemd_service(mount_point)
        else:
            install_path = self.INITD_PATH
            install_content = INITD_SERVICE_FILE

        self.ui.progress("Installing: ", 2)

        # Write service file
        with open(install_path, 'w') as f:
            f.write(install_content)

        # Reload systemd to pick up changes
        if self.system_info.has_systemd:
            os.system('systemctl daemon-reload')
            os.system('systemctl enable radiuid')
        else:
            os.system('chmod 777 /etc/init.d/radiuid')
            os.system('chkconfig radiuid on')

    def install_bash_completion(self) -> None:
        """Install bash completion script for RadiUID CLI."""
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
            remove_config: Whether to remove configuration files

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

        # Remove service file
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

        # Remove main executable
        print("Removing RadiUID executable...")
        bin_path = os.path.join(self.BIN_PATH, "radiuid")
        if os.path.exists(bin_path):
            try:
                os.remove(bin_path)
            except OSError as e:
                print(self.ui.color(f"Warning: Could not remove {bin_path}: {e}", self.ui.yellow))
                success = False
        self.ui.progress("Removing Executable: ", 1)

        # Remove bash completion
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
            print("Removing configuration files...")
            if os.path.exists(self.CONFIG_PATH):
                import shutil
                try:
                    shutil.rmtree(self.CONFIG_PATH)
                except OSError as e:
                    print(self.ui.color(f"Warning: Could not remove {self.CONFIG_PATH}: {e}", self.ui.yellow))
                    success = False
            self.ui.progress("Removing Configuration: ", 1)
        else:
            print(self.ui.color(f"Configuration preserved at {self.CONFIG_PATH}", self.ui.cyan))

        return success

    def install_freeradius(self) -> str:
        """
        Install FreeRADIUS server.

        Returns:
            'PASS' on success, 'FAIL' on failure
        """
        pkg_manager = self.system_info.package_manager

        print(f"Installing FreeRADIUS using {pkg_manager}...")
        os.system(f'{pkg_manager} install freeradius -y')

        # Refresh service name detection
        self.system_info.refresh()
        radius_service = self.system_info.radius_service_name

        # Start the service
        self.service_controller.control_service("start", radius_service)
        time.sleep(3)

        # Check if running
        status = self.service_controller.control_service("status", radius_service)
        if status['status'] == "running":
            print(self.ui.color("****************FreeRADIUS is Now Running!****************", self.ui.green))
            return "PASS"
        else:
            print(self.ui.color("****************Something went wrong with the FreeRADIUS install****************", self.ui.red))
            print(self.ui.color("****************You may need to run some system updates for it to install correctly****************", self.ui.red))
            return "FAIL"

    def _get_bash_completion_script(self) -> str:
        """Get the bash completion script content."""
        return '''#!/bin/bash

#####  RadiUID Server BASH Complete Script  #####

_radiuid_complete()
{
  local cur prev
  COMPREPLY=()
  cur=${COMP_WORDS[COMP_CWORD]}
  prev=${COMP_WORDS[COMP_CWORD-1]}
  prev2=${COMP_WORDS[COMP_CWORD-2]}
  if [ $COMP_CWORD -eq 1 ]; then
    COMPREPLY=( $(compgen -W "run install show set push tail clear edit service request version" -- $cur) )
  elif [ $COMP_CWORD -eq 2 ]; then
    case "$prev" in
      show)
        COMPREPLY=( $(compgen -W "log acct-logs livelog run config clients status mappings" -- $cur) )
        ;;
      "set")
        COMPREPLY=( $(compgen -W "tlsversion radiusstopaction looptime logfile maxloglines radiuslogpath acctlogcopypath userdomain timeout target client munge livelog" -- $cur) )
        ;;
      push)
        local targets=$(for target in `radiuid targets`; do echo $target ; done)
        COMPREPLY=( $(compgen -W "${targets} all" -- ${cur}) )
        ;;
      "tail")
        COMPREPLY=( $(compgen -W "log" -- $cur) )
        ;;
      "clear")
        COMPREPLY=( $(compgen -W "log acct-logs livelog target mappings client munge" -- $cur) )
        ;;
      edit)
        COMPREPLY=( $(compgen -W "config clients" -- $cur) )
        ;;
      "service")
        COMPREPLY=( $(compgen -W "radiuid freeradius all" -- $cur) )
        ;;
      "request")
        COMPREPLY=( $(compgen -W "xml-update munge-test auto-complete reinstall uninstall freeradius-install set-mount" -- $cur) )
        ;;
      *)
        ;;
    esac
  elif [ $COMP_CWORD -eq 3 ]; then
    case "$prev" in
      config)
        if [ "$prev2" == "show" ]; then
          COMPREPLY=( $(compgen -W "xml set" -- $cur) )
        fi
        ;;
      livelog)
        if [ "$prev2" == "set" ]; then
          COMPREPLY=( $(compgen -W "file tracker enabled" -- $cur) )
        elif [ "$prev2" == "clear" ]; then
          COMPREPLY=( $(compgen -W "tracker" -- $cur) )
        fi
        ;;
      reinstall)
        if [ "$prev2" == "request" ]; then
          COMPREPLY=( $(compgen -W "replace-config keep-config" -- $cur) )
        fi
        ;;
      uninstall)
        if [ "$prev2" == "request" ]; then
          COMPREPLY=( $(compgen -W "keep-config remove-config" -- $cur) )
        fi
        ;;
      set-mount)
        if [ "$prev2" == "request" ]; then
          COMPREPLY=( $(compgen -W "none" -- $cur) )
        fi
        ;;
      client)
        if [ "$prev2" == "clear" ]; then
          local clients=$(for client in `radiuid clients`; do echo $client ; done)
          COMPREPLY=( $(compgen -W "${clients} all" -- ${cur}) )
        elif [ "$prev2" == "set" ]; then
          COMPREPLY=( $(compgen -W "ipv4 ipv6" -- $cur) )
        fi
        ;;
      freeradius|radiuid)
        if [ "$prev2" == "service" ]; then
          COMPREPLY=( $(compgen -W "start stop restart" -- $cur) )
        fi
        ;;
      mappings)
        local targets=$(for target in `radiuid targets`; do echo $target ; done)
        if [ "$prev2" == "show" ]; then
          COMPREPLY=( $(compgen -W "${targets} all consistency" -- ${cur}) )
        elif [ "$prev2" == "clear" ]; then
          COMPREPLY=( $(compgen -W "${targets} all" -- ${cur}) )
        fi
        ;;
      target)
        local targets=$(for target in `radiuid targets`; do echo $target ; done)
        if [ "$prev2" == "set" ]; then
          COMPREPLY=( $(compgen -W "${targets}" -- ${cur}) )
        elif [ "$prev2" == "clear" ]; then
          COMPREPLY=( $(compgen -W "${targets} all" -- ${cur}) )
        fi
        ;;
      all)
        if [ "$prev2" == "service" ]; then
          COMPREPLY=( $(compgen -W "start stop restart" -- $cur) )
        fi
        ;;
      *)
        ;;
    esac
  elif [ $COMP_CWORD -eq 4 ]; then
    case "$prev" in
      enabled)
        if [ "$prev2" == "livelog" ]; then
          COMPREPLY=( $(compgen -W "on off true false" -- $cur) )
        fi
        ;;
      *)
        ;;
    esac
  fi
}

complete -F _radiuid_complete radiuid
'''
