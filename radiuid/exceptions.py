#!/usr/bin/env python3
"""
RadiUID Exception Classes
Custom exceptions for better error handling
"""

class RadiUIDError(Exception):
    """Base exception for all RadiUID errors"""
    pass

class ConfigurationError(RadiUIDError):
    """Raised when configuration file issues occur"""
    pass

class FirewallConnectionError(RadiUIDError):
    """Raised when unable to connect to the firewall"""
    pass

class FirewallAPIError(RadiUIDError):
    """Raised when firewall API returns an error"""
    pass

class ValidationError(RadiUIDError):
    """Raised when input validation fails"""
    pass

class FileOperationError(RadiUIDError):
    """Raised when file operations fail"""
    pass

class RadiusLogError(RadiUIDError):
    """Raised when RADIUS log processing fails"""
    pass

class ServiceError(RadiUIDError):
    """Raised when system service operations fail"""
    pass
