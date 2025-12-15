#!/usr/bin/env python3
"""
System Information Module
Encapsulates system detection and configuration
"""

import subprocess
import platform
from typing import Optional

from .constants import PackageManagers, Services, Paths
from .logging_config import get_logger

logger = get_logger('system_info')


class SystemInfo:
    """Encapsulates system information and detection"""

    def __init__(self):
        self._systemd: Optional[bool] = None
        self._pkg_manager: Optional[str] = None
        self._radius_service: Optional[str] = None
        self._client_config_path: Optional[str] = None
        self._in_container: Optional[bool] = None
        self._os_version: Optional[str] = None

    @property
    def has_systemd(self) -> bool:
        """Check if the system uses systemd"""
        if self._systemd is None:
            try:
                status, output = subprocess.getstatusoutput("systemctl")
                self._systemd = len(output) > 50 and "Operation not permitted" not in output
            except (OSError, subprocess.SubprocessError) as e:
                logger.debug(f"Error checking systemd: {e}")
                self._systemd = False
        return self._systemd

    @property
    def package_manager(self) -> str:
        """Detect the system package manager (prefers dnf over yum)"""
        if self._pkg_manager is None:
            # Check each package manager in order of preference
            for mgr in PackageManagers.MANAGERS:
                try:
                    status, output = subprocess.getstatusoutput(f"which {mgr}")
                    if status == 0:  # Found the package manager
                        self._pkg_manager = mgr
                        logger.debug(f"Found package manager: {mgr}")
                        break
                except (OSError, subprocess.SubprocessError):
                    pass

            if self._pkg_manager is None:
                self._pkg_manager = "unknown"
                logger.warning("Could not detect package manager")

        return self._pkg_manager

    @property
    def radius_service_name(self) -> str:
        """Detect FreeRADIUS service name"""
        if self._radius_service is None:
            check_results = {}

            for name in Services.RADIUS_NAMES:
                try:
                    if self.has_systemd:
                        status, output = subprocess.getstatusoutput(f"systemctl status {name}")
                        check_results[len(output) - len(name)] = name
                    else:
                        status, output = subprocess.getstatusoutput(f"service {name} status")
                        if "stopped" in output:
                            check_results[1000] = name
                        check_results[len(output) - len(name)] = name
                except (OSError, subprocess.SubprocessError):
                    pass

            if len(check_results) < 2:
                self._radius_service = "uninstalled"
            else:
                # Return the one with the longest output
                self._radius_service = check_results[max(check_results.keys())]

        return self._radius_service

    @property
    def client_config_path(self) -> str:
        """Detect FreeRADIUS client config path"""
        if self._client_config_path is None:
            paths = [Paths.RADDB_CLIENTS, Paths.FREERADIUS_CLIENTS]
            check_results = {}

            for path in paths:
                try:
                    status, output = subprocess.getstatusoutput(f"ls {path}")
                    check_results[status] = path
                except (OSError, subprocess.SubprocessError):
                    pass

            self._client_config_path = check_results.get(0, Paths.RADDB_CLIENTS)

        return self._client_config_path

    @property
    def in_container(self) -> bool:
        """Check if running in a container"""
        if self._in_container is None:
            try:
                status, output = subprocess.getstatusoutput("ls /.dockerenv")
                self._in_container = "No such" not in output
            except (OSError, subprocess.SubprocessError):
                self._in_container = False

        return self._in_container

    @property
    def os_version(self) -> str:
        """Get OS version information"""
        if self._os_version is None:
            try:
                self._os_version = platform.platform()
                if self.in_container:
                    self._os_version += " (Docker Container)"
            except OSError:
                self._os_version = platform.system()

        return self._os_version

    def refresh(self):
        """Clear cached values to force re-detection"""
        self._systemd = None
        self._pkg_manager = None
        self._radius_service = None
        self._client_config_path = None
        self._in_container = None
        self._os_version = None


# Global singleton instance
_system_info = None


def get_system_info() -> SystemInfo:
    """Get the global SystemInfo singleton"""
    global _system_info
    if _system_info is None:
        _system_info = SystemInfo()
    return _system_info
