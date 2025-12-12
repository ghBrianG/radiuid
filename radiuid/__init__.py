#!/usr/bin/env python3
"""
RadiUID - RADIUS User-ID Integration for Palo Alto Firewalls
Python 3 Port by Brian Griffith
Originally by John W Kerns
"""

from .constants import VERSION
from .exceptions import (
    RadiUIDError,
    ConfigurationError,
    FirewallConnectionError,
    FirewallAPIError,
    ValidationError,
    FileOperationError,
    RadiusLogError,
    ServiceError
)
from .logging_config import setup_logging, get_logger
from .system_info import SystemInfo, get_system_info
from .context import AppContext, RadiUIDConfig, FirewallTarget, get_context

# Import extracted classes
from .ui.interface import UserInterface, user_interface
from .core.data_processor import DataProcessor, data_processing
from .core.config_manager import ConfigManager
from .core.file_manager import FileManager
from .core.service import RadiUIDService
from .firewall.palo_alto import PaloAltoFirewall, palo_alto_firewall_interaction

# Import installer classes
from .installer.system_setup import ServiceController, SystemInstaller
from .installer.wizard import InstallationWizard

# Import CLI
from .cli.main import CLIRouter, main as cli_main

__version__ = VERSION
__all__ = [
    # Version
    'VERSION',
    # Exceptions
    'RadiUIDError',
    'ConfigurationError',
    'FirewallConnectionError',
    'FirewallAPIError',
    'ValidationError',
    'FileOperationError',
    'RadiusLogError',
    'ServiceError',
    # Logging
    'setup_logging',
    'get_logger',
    # System
    'SystemInfo',
    'get_system_info',
    # Context
    'AppContext',
    'RadiUIDConfig',
    'FirewallTarget',
    'get_context',
    # UI
    'UserInterface',
    'user_interface',
    # Core
    'DataProcessor',
    'data_processing',
    'ConfigManager',
    'FileManager',
    'RadiUIDService',
    # Firewall
    'PaloAltoFirewall',
    'palo_alto_firewall_interaction',
    # Installer
    'ServiceController',
    'SystemInstaller',
    'InstallationWizard',
    # CLI
    'CLIRouter',
    'cli_main',
]
