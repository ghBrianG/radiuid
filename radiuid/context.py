#!/usr/bin/env python3
"""
Application Context Module
Centralized state management replacing global variables
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from xml.etree import ElementTree

from .logging_config import get_logger
from .system_info import get_system_info, SystemInfo
from .constants import TLSVersions

logger = get_logger('context')


@dataclass
class FirewallTarget:
    """Represents a Palo Alto firewall target configuration"""
    hostname: str
    vsys: str
    username: str = ""
    password: str = ""
    port: str = "443"
    api_key: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'FirewallTarget':
        """Create FirewallTarget from dictionary"""
        return cls(
            hostname=data.get('hostname', ''),
            vsys=data.get('vsys', '1'),
            username=data.get('username', ''),
            password=data.get('password', ''),
            port=data.get('port', '443'),
            api_key=data.get('apikey')
        )

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for XML serialization"""
        result = {
            'hostname': self.hostname,
            'vsys': self.vsys,
            'username': self.username,
            'password': self.password,
            'port': self.port
        }
        if self.api_key:
            result['apikey'] = self.api_key
        return result

    @property
    def identifier(self) -> str:
        """Return hostname:vsys identifier"""
        return f"{self.hostname}:vsys{self.vsys}"


@dataclass
class RadiUIDConfig:
    """Holds all parsed configuration values"""
    # Paths
    config_file: str = ""
    log_file: str = "/var/log/radiuid.log"
    radius_log_path: str = "/var/log/freeradius/radacct/"
    acct_log_copy_path: Optional[str] = None
    xml_output_path: Optional[str] = None

    # Logging
    max_log_lines: int = 10000

    # UID Settings
    user_domain: Optional[str] = None
    timeout: int = 60  # Minutes until User-ID mapping expires on firewall

    # Misc
    loop_time: int = 10
    tls_version: str = "1.2"
    radius_stop_action: str = "clear"

    # Search Terms
    ip_address_term: str = "Framed-IP-Address"
    username_term: str = "User-Name"
    delineator_term: str = "[PARAGRAPH]"

    # Munge configuration
    munge_config: Optional[Dict[str, Any]] = None
    to_munge: bool = False

    # Live log file settings (for NPS/continuously written logs)
    live_log_file: Optional[str] = None  # Path to live log file being written to
    live_log_tracker: Optional[str] = None  # Path to position tracker file
    live_log_enabled: bool = False  # Whether to use live log processing

    # NPS CSV parsing settings (0-based column indices)
    # Set to -1 to enable auto-detection using RADIUS attribute numbers
    nps_ip_column: int = 0  # Column with IP (or -1 to find attr 8/4108)
    nps_username_column: int = 1  # Column with username (or -1 to find attr 1/4129)
    nps_packet_type_column: int = 6  # Column with packet type code

    # Max UIDs per API call
    max_uids_per_call: int = 50

    @property
    def tls_protocol(self) -> Optional[int]:
        """Get SSL protocol constant for the configured TLS version"""
        return TLSVersions.get_protocol(self.tls_version)


class AppContext:
    """
    Singleton holding application runtime state.
    Replaces all global variables from the monolithic radiuid.py
    """
    _instance: Optional['AppContext'] = None

    def __init__(self):
        # Configuration
        self.config: RadiUIDConfig = RadiUIDConfig()
        self.targets: List[FirewallTarget] = []

        # System information
        self.system_info: SystemInfo = get_system_info()

        # XML configuration state (for config modifications)
        self._config_root: Optional[ElementTree.Element] = None
        self._config_comment: str = ""

        # Runtime state
        self._initialized: bool = False

        # Command run format (python radiuid.py vs radiuid)
        self._run_cmd: str = "radiuid"

        # TLS configuration object
        self.tls_obj: Optional[int] = None

        # Legacy config dict for XML compatibility
        self._config_dict: Optional[Dict[str, Any]] = None

    @classmethod
    def get_instance(cls) -> 'AppContext':
        """Get the global AppContext singleton"""
        if cls._instance is None:
            cls._instance = AppContext()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (primarily for testing)"""
        cls._instance = None

    @property
    def run_cmd(self) -> str:
        """Get the command used to invoke RadiUID"""
        return self._run_cmd

    @run_cmd.setter
    def run_cmd(self, value: str) -> None:
        """Set the command used to invoke RadiUID"""
        self._run_cmd = value

    @property
    def config_root(self) -> Optional[ElementTree.Element]:
        """Get the XML configuration root element"""
        return self._config_root

    @config_root.setter
    def config_root(self, value: ElementTree.Element) -> None:
        """Set the XML configuration root element"""
        self._config_root = value

    @property
    def config_comment(self) -> str:
        """Get the XML configuration comment block"""
        return self._config_comment

    @config_comment.setter
    def config_comment(self, value: str) -> None:
        """Set the XML configuration comment block"""
        self._config_comment = value

    @property
    def config_dict(self) -> Optional[Dict[str, Any]]:
        """Get the configuration as a dictionary (for legacy compatibility)"""
        return self._config_dict

    @config_dict.setter
    def config_dict(self, value: Dict[str, Any]) -> None:
        """Set the configuration dictionary"""
        self._config_dict = value

    @property
    def is_initialized(self) -> bool:
        """Check if context has been initialized with config"""
        return self._initialized

    def mark_initialized(self) -> None:
        """Mark the context as initialized"""
        self._initialized = True

    def get_target(self, identifier: str) -> Optional[FirewallTarget]:
        """
        Get a target by identifier (hostname:vsysN)

        Args:
            identifier: Target identifier like 'fw01.example.com:vsys1'

        Returns:
            FirewallTarget if found, None otherwise
        """
        for target in self.targets:
            if target.identifier == identifier:
                return target
        return None

    def get_target_by_hostname(self, hostname: str, vsys: str) -> Optional[FirewallTarget]:
        """
        Get a target by hostname and vsys

        Args:
            hostname: Firewall hostname
            vsys: Virtual system ID

        Returns:
            FirewallTarget if found, None otherwise
        """
        for target in self.targets:
            if target.hostname == hostname and target.vsys == vsys:
                return target
        return None

    def add_target(self, target: FirewallTarget) -> None:
        """Add a firewall target"""
        existing = self.get_target_by_hostname(target.hostname, target.vsys)
        if existing:
            # Update existing target
            idx = self.targets.index(existing)
            self.targets[idx] = target
        else:
            self.targets.append(target)

    def remove_target(self, hostname: str, vsys: str) -> bool:
        """
        Remove a target by hostname and vsys

        Returns:
            True if target was removed, False if not found
        """
        target = self.get_target_by_hostname(hostname, vsys)
        if target:
            self.targets.remove(target)
            return True
        return False

    def clear_targets(self) -> None:
        """Remove all firewall targets"""
        self.targets.clear()

    def get_targets_as_dicts(self) -> List[Dict[str, str]]:
        """Get all targets as list of dictionaries (for legacy compatibility)"""
        return [t.to_dict() for t in self.targets]


def get_context() -> AppContext:
    """Get the global AppContext singleton"""
    return AppContext.get_instance()
