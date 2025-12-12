#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for RadiUID tests
"""

import os
import sys
import tempfile
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radiuid.context import AppContext, RadiUIDConfig
from radiuid.ui.interface import UserInterface
from radiuid.core.data_processor import DataProcessor
from radiuid.core.file_manager import FileManager
from radiuid.core.config_manager import ConfigManager
from radiuid.firewall.palo_alto import PaloAltoFirewall


@pytest.fixture
def app_context():
    """Create a fresh AppContext for testing"""
    AppContext.reset_instance()
    ctx = AppContext.get_instance()
    return ctx


@pytest.fixture
def user_interface():
    """Create a UserInterface instance"""
    return UserInterface()


@pytest.fixture
def data_processor(app_context):
    """Create a DataProcessor instance"""
    return DataProcessor(context=app_context)


@pytest.fixture
def file_manager(app_context, user_interface):
    """Create a FileManager instance"""
    return FileManager(context=app_context, ui=user_interface)


@pytest.fixture
def config_manager(app_context, user_interface):
    """Create a ConfigManager instance"""
    return ConfigManager(context=app_context, ui=user_interface)


@pytest.fixture
def firewall(app_context, user_interface):
    """Create a PaloAltoFirewall instance"""
    return PaloAltoFirewall(context=app_context, ui=user_interface)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_radius_log(temp_dir):
    """Create a sample FreeRADIUS log file"""
    content = """Acct-Session-Id = "00000001"
User-Name = "testuser"
Framed-IP-Address = 192.168.1.100
Acct-Status-Type = Start
Timestamp = 1234567890

Acct-Session-Id = "00000002"
User-Name = "admin"
Framed-IP-Address = 10.0.0.50
Acct-Status-Type = Start
Timestamp = 1234567891
"""
    filepath = os.path.join(temp_dir, "radius.log")
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath


@pytest.fixture
def sample_nps_csv_log(temp_dir):
    """Create a sample NPS CSV log file"""
    content = """10.1.75.8,testuser,12/11/2025,17:05:02,IAS,JSW-NPS,4,1,0,host/PC001,10.1.75.8
10.1.50.100,adminuser,12/11/2025,17:10:15,IAS,JSW-NPS,4,1,0,host/PC002,10.1.50.100
192.168.1.50,domain\\jsmith,12/11/2025,17:15:30,IAS,JSW-NPS,4,1,0,host/PC003,192.168.1.50
"""
    filepath = os.path.join(temp_dir, "nps.log")
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath


@pytest.fixture
def sample_nps_mixed_log(temp_dir):
    """Create a sample NPS log with XML header and CSV data"""
    content = """<Event><Computer-Name data_type="1">JSW-NPS</Computer-Name></Event>
<Event><Computer-Name data_type="1">JSW-NPS</Computer-Name></Event>
10.1.75.8,testuser,12/11/2025,17:05:02,IAS,JSW-NPS,4,1,0,host/PC001,10.1.75.8
10.1.50.100,adminuser,12/11/2025,17:10:15,IAS,JSW-NPS,4,1,0,host/PC002,10.1.50.100
"""
    filepath = os.path.join(temp_dir, "nps_mixed.log")
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath


@pytest.fixture
def sample_mappings():
    """Sample IP to user mappings"""
    return {
        "192.168.1.100": {"username": "user1", "status": "start"},
        "192.168.1.101": {"username": "user2", "status": "start"},
        "10.0.0.50": {"username": "admin", "status": "stop"},
    }


@pytest.fixture
def sample_targets():
    """Sample firewall targets"""
    return [
        {"hostname": "fw01.example.com", "vsys": "1", "apikey": "testkey123"},
        {"hostname": "192.168.1.1", "vsys": "2", "apikey": "testkey456"},
    ]
