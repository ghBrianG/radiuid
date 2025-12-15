#!/usr/bin/env python3
"""
RadiUID Constants and Configuration
Extracted from main radiuid.py for better organization
"""

# Version Information
VERSION = "v3.0.0"

# File Paths
class Paths:
    """System file paths"""
    ETC_CONFIG_FILE = '/etc/radiuid/radiuid.yaml'
    RADDB_CLIENTS = '/etc/raddb/clients.conf'
    FREERADIUS_CLIENTS = '/etc/freeradius/clients.conf'

# Limits and Thresholds
class Limits:
    """System limits and thresholds"""
    # 1440 minutes = 24 hours, matches Palo Alto default User-ID TTL
    # This is how long mappings persist on the firewall before auto-expiring
    MAX_TIMEOUT = 1440

    # Palo Alto User-ID API enforces a limit of 50 UIDs per API call
    # Larger batches must be split into multiple requests
    MAX_UIDS_PER_CALL = 50

# Service Names
class Services:
    """Service name options"""
    RADIUS_NAMES = ["radiusd", "freeradius"]

# Package Managers
class PackageManagers:
    """Supported package managers (in order of preference)"""
    MANAGERS = ["dnf", "yum", "apt", "apt-get"]

# ANSI Color Codes
class Colors:
    """ANSI color codes for terminal output"""
    BLACK = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

# Regex Patterns
class RegexPatterns:
    """Common regex patterns used throughout the application"""
    IPV4 = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    IPV4_WITH_CIDR = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:[0-9]|1[0-9]|2[0-9]|3[0-2]?))$"
    DOMAIN_CHARS = r"^[a-zA-Z0-9\-\.]+$"
    USERNAME_CHARS = r"^[a-zA-Z0-9_\.]+$"
    INVALID_PASSWORD_CHARS = r"\&|\<|\>"

# FreeRADIUS Log Terms
class RadiusLogTerms:
    """FreeRADIUS accounting log field identifiers"""
    USERNAME = "User-Name"
    IP_ADDRESS = "Framed-IP-Address"
    DELINEATOR = "[PARAGRAPH]"  # Special keyword for paragraph separation
    ACCT_STATUS_TYPE = "Acct-Status-Type"
